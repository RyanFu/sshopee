from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn import metrics
from shopee_api import mydb
import time, csv

sql = "select distinct name, category_id from items where account like '%my' and category_id in (select category_id from (select count (category_id) as num, category_id from items group by category_id) where num > 50)"
con = mydb(sql)
print('loaded ', len(con), time.ctime())
x, y = [i[0] for i in con], [i[1].split('.')[-1] for i in con]
x_train, x_test, y_train, y_test = train_test_split(x, y, stratify=y, random_state=12)
names = [i for i in x_test]
myvt = TfidfVectorizer()
x_train = myvt.fit_transform(x_train)
x_test = myvt.transform(x_test)
clf = MultinomialNB()
clf = clf.fit(x_train, y_train)
print('trained ', time.ctime())

predicted = clf.predict(x_test)
print('predicted ', time.ctime())
print(metrics.classification_report(y_test, predicted))
values = []
for i in range(x_test.shape[0]):
    name, ori, pre = names[i], y_test[i], predicted[i]
    values.append([name, ori, pre])
with open('d://out.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerows(values)