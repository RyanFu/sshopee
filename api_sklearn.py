from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.pipeline import make_pipeline, Pipeline
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.preprocessing import MaxAbsScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import SGDClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import classification_report
from api_tools import mydb
import time, numpy, joblib, os, csv, pandas

def save_data(site, min_sample, max_sample):
    sql = "select distinct name, category_id, model_name from items where account like '%{}' order by sold".format(site)
    #sql = "select distinct cname, category_id from ((select distinct parent_sku, model_sku, category_id from items where account like '%{}' order by sold) inner join zong on model_sku = sku or parent_sku = sku)".format(site)
    con = mydb(sql)
    mp = {}
    for name, cat, cat2 in con:
        cat = cat.split(".")[-1]
        cat = cat2 if len(cat2) > 1 and cat2.isdigit() else cat 
        name_list = mp.get(cat, [])
        name_list.append(name)
        mp[cat] = name_list
    data = []
    max_length = max([len(i) for i in mp.values()])
    for cat in mp.keys():
        name_list = mp[cat]
        length = len(name_list)
        if length > min_sample:
            num_cut = int((length - max_sample)/(max_length - max_sample) * 100) + max_sample
            name_list = name_list[:num_cut]
            for name in name_list:
                data.append((name, cat))
    x, y = [i[0] for i in data], [i[1] for i in data]
    num_sample, num_class = len(x), len(set(y))
    print(f"{num_sample} samples for {num_class} classes saved")
    
    df = pandas.DataFrame(data, columns=['name', 'cat'])
    file = 'd:/train_' + site + '.csv'
    df.to_csv(file, index=False)
    print('train file saved')

def load_data(site):
    file = 'd:/train_' + site + '.csv'
    df = pandas.read_csv(file)
    x, y = df['name'], df['cat']
    x, y = list(x), list(y)
    data = (x, y)
    return data
    
def pipe_train(x, y, pipe_name, debug=False):
    #y = [int(i) for i in y]
    if debug:
        x_train, x_test, y_train, y_test = train_test_split(x, y, stratify=y, random_state=12)
    else:
        x_train,y_train = x, y
    num_sample, num_class = len(x_train), len(set(y_train))
    pipe = Pipeline([
    ["vt", CountVectorizer(stop_words='english')],
    ["tf", TfidfTransformer()],
    ["sc", MaxAbsScaler()],
    #["clf", KNeighborsClassifier()],
    #["clf", MultinomialNB(),] 
    #["clf", SGDClassifier(loss='hinge', penalty='l2',alpha=1e-3, random_state=42, max_iter=50, tol=None)],
    ["clf", MLPClassifier(random_state=1, max_iter=15, verbose=True, early_stopping=True)],

    ])
    #MY e: NB 47 SGD 60 MLP 72  KNN 60
    pipe.fit(x_train, y_train)
    pipe_path = f"d:/sshopee/static/{pipe_name}_train_{num_sample}samples_{num_class}classes_{int(time.time())}.joblib"
    joblib.dump(pipe, pipe_path)
    print('saved', time.ctime())
    if debug:
        predicted = pipe.predict(x_test)
        report = classification_report(y_test, predicted)
        print(report)


def pipe_predict(x_test, model_name):
    model_path = "./static/{}.joblib".format(model_name)
    model = joblib.load(model_path)
    predicted = model.predict(x_test)
    predicted = [str(i) for i in predicted]
    return predicted


if __name__ == '__main__':
    site = 'ph'
    save_data(site, 50,  300)
    x, y = load_data(site)
    pipe_train(x, y, site, False)
