import torch, time, csv
from sklearn.model_selection import train_test_split
from torchtext.datasets import AG_NEWS
from torchtext.data.utils import get_tokenizer
from collections import Counter
from torchtext.vocab import Vocab
from torch import nn
from api_tools import mydb
from torch.utils.data import DataLoader

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
torch.manual_seed(12)

def mark_labels(ar):
    st = list(set(ar))
    mp = {}
    for i in range(len(st)):
        k, v = st[i], i + 1
        mp[k] = v
    re = [mp[i] for i in ar]
    return (re, len(st))

def load_data(site):
    sql = "select distinct name, cat from temp"
    con = mydb(sql)
    x, y = [i[0] for i in con], [i[1] for i in con]
    y, num_class = mark_labels(y)
    x_train, x_test, y_train, y_test = train_test_split(x, y, stratify=y, random_state=12, test_size=0.1)
    train, test = list(zip(y_train, x_train)), list(zip(y_test, x_test))
    num_train, num_test = len(x_train), len(x_test)
    print(f"{num_class} classes, {num_train} for training, {num_test} to test")
    return (train, test)

tokenizer = get_tokenizer('basic_english')
train_iter, valid_iter = load_data('my')
counter = Counter()
for (label, line) in train_iter:
    counter.update(tokenizer(line))
vocab = Vocab(counter, min_freq=1)

text_pipeline = lambda x: [vocab[token] for token in tokenizer(x)]
label_pipeline = lambda x: int(x) - 1

def collate_batch(batch):
    label_list, text_list, offsets = [], [], [0]
    for (_label, _text) in batch:
         label_list.append(label_pipeline(_label))
         processed_text = torch.tensor(text_pipeline(_text), dtype=torch.int64)
         text_list.append(processed_text)
         offsets.append(processed_text.size(0))
    label_list = torch.tensor(label_list, dtype=torch.int64)
    offsets = torch.tensor(offsets[:-1]).cumsum(dim=0)
    text_list = torch.cat(text_list)
    return label_list.to(device), text_list.to(device), offsets.to(device)    

class Classifier1(nn.Module):
    def __init__(self, vocab_size, embed_dim, num_class):
        super(Classifier1, self).__init__()
        self.embedding = nn.EmbeddingBag(vocab_size, embed_dim, sparse=True)
        self.fc = nn.Linear(embed_dim, num_class)
        self.init_weights()

    def init_weights(self):
        initrange = 0.5
        self.embedding.weight.data.uniform_(-initrange, initrange)
        self.fc.weight.data.uniform_(-initrange, initrange)
        self.fc.bias.data.zero_()

    def forward(self, text, offsets):
        embedded = self.embedding(text, offsets)
        return self.fc(embedded)

class RNN(nn.Module):
    def __init__(self, vocab_size, embed_dim, num_class, hidden_size, num_layers):
        self.embedding = nn.EmbeddingBag(vocab_size, embed_dim, )
        self.lstm = nn.LSTM(embed_dim, hidden_size, num_layers,
            bidirectional=True, batch_first=True, dropout=0.1)
        self.fc = nn.Linear(hidden_size * 2, num_class)
    
    def forward(self, x):
        x, _  = x
        out = self.embedding(x)
        out, _ = self.lstm(out)
        out = self.fc(out[:, -1, :])
        return out

num_class = len(set([label for (label, text) in train_iter]))
vocab_size = len(vocab)
emsize = 128

model = Classifier1(vocab_size, emsize, num_class).to(device)
model = RNN(vocab_size, emsize, num_class, 64, 2).to(device)
print(f'vocabulary_list_length is {vocab_size}, embeding size is {emsize}')
print(model)

def train(dataloader):
    model.train()
    total_acc, total_count = 0, 0
    log_interval = int(len(dataloader)/5)
    start_time = time.time()

    for idx, (label, text, offsets) in enumerate(dataloader):
        optimizer.zero_grad()
        predited_label = model(text, offsets)
        loss = criterion(predited_label, label)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 0.1)
        optimizer.step()
        total_acc += (predited_label.argmax(1) == label).sum().item()
        total_count += label.size(0)
        if idx % log_interval == 0 and idx > 0:
            elapsed = time.time() - start_time
            print(label.size(), text.size(), offsets.size())
            print('epoch {:3d} {:5d}/{:5d} batches accuracy {:8.3f}'.format(epoch, 
                                        idx, len(dataloader),
                                        total_acc/total_count))
            total_acc, total_count = 0, 0
            start_time = time.time()

def evaluate(dataloader):
    model.eval()
    total_acc, total_count = 0, 0

    with torch.no_grad():
        for idx, (label, text, offsets) in enumerate(dataloader):
            predited_label = model(text, offsets)
            loss = criterion(predited_label, label)
            total_acc += (predited_label.argmax(1) == label).sum().item()
            total_count += label.size(0)
    return total_acc/total_count

from torch.utils.data.dataset import random_split
# Hyperparameters
EPOCHS = 100 # epoch
LR = 5  # learning rate
BATCH_SIZE = 8 # batch size for training
  
criterion = torch.nn.CrossEntropyLoss()
optimizer = torch.optim.SGD(model.parameters(), lr=LR)
scheduler = torch.optim.lr_scheduler.StepLR(optimizer, 1.0, gamma=0.1)
total_accu = None

train_dataloader = DataLoader(train_iter, batch_size=BATCH_SIZE,
                              shuffle=True, collate_fn=collate_batch)
valid_dataloader = DataLoader(valid_iter, batch_size=BATCH_SIZE,
                              shuffle=True, collate_fn=collate_batch)

best_acc, best_ep = 0, 0
for epoch in range(1, EPOCHS + 1):
    epoch_start_time = time.time()
    train(train_dataloader)
    accu_val = evaluate(valid_dataloader)
    if total_accu is not None and total_accu > accu_val:
      scheduler.step()
    else:
       total_accu = accu_val
    print('end of epoch {:3d} time: {:5.2f}s  valid accuracy {:8.3f} '.format(epoch,
                                           time.time() - epoch_start_time,
                                           accu_val))

    if accu_val > best_acc + 0.0001:
        best_acc, best_ep = accu_val, epoch
    elif epoch - best_ep >= 5:
        break
    print(f'Best score is {best_acc} at round {best_ep}\n')
print('all done')
print(f'Best score is {best_acc} at round {best_ep}')