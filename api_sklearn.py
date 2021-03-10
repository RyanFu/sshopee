from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.pipeline import make_pipeline, Pipeline
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.preprocessing import MaxAbsScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import SGDClassifier
from sklearn.neural_network import MLPClassifier
from shopee_api import mydb
import time, numpy, joblib, os, csv

def load_data(site):
    #sql = "select name, category_id from (select distinct parent_sku, model_sku, category_id from items where account like '%{}' and category_id in (select category_id from items group by category_id having count(distinct item_id) > 50)) as temp inner join zong on temp.model_sku = zong.sku or temp.parent_sku = zong.sku;".format(site)
    sql = "select distinct name, category_id from items where account like '%{}' and category_id in (select category_id from items group by category_id having count(distinct item_id) > 50)".format(site)
    #sql = "select name, cat from temp"
    con = mydb(sql)
    print('loaded ', len(con), time.ctime())
    x, y = [i[0] for i in con], [i[1].split(".")[-1] for i in con]
    return (x, y)

def pipe_train(x, y, pipe_name, debug=False):
    #y = [int(i) for i in y]
    if debug:
        x_train, x_test, y_train, y_test = train_test_split(x, y, stratify=y, random_state=12)
    else:
        x_train,y_train = x, y
    pipe = Pipeline([
    ["vt", CountVectorizer(stop_words='english')],
    ["tf", TfidfTransformer()],
    ["sc", MaxAbsScaler()],
    #["clf", KNeighborsClassifier()],
    #["clf", MultinomialNB(),] 
    #["clf", SGDClassifier(loss='hinge', penalty='l2',alpha=1e-3, random_state=42, max_iter=5, tol=None)],
    ["clf", MLPClassifier(random_state=1, max_iter=100, verbose=True, early_stopping=True)],

    ])
    #MY e: NB 47 SGD 60 MLP 67  KNN 60
    #my z:mlp 59
    pipe.fit(x_train, y_train)
    pipe_path = "d://shopee/static/{}_train.joblib".format(pipe_name)
    joblib.dump(pipe, pipe_path)
    print('saved', time.ctime())
    if debug:
        predicted = pipe.predict(x_test)
        print('predicted', time.ctime())
        print(numpy.mean(predicted == y_test))
        values = list(zip(x_test, y_test, predicted))
        with open('d://out.csv', 'w+', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerows(values)
        print('writed')

def pipe_predict(x_test, model_name):
    model_path = "./static/{}.joblib".format(model_name)
    model = joblib.load(model_path)
    predicted = model.predict(x_test)
    data = list(zip(x_test, predicted))
    return data

def temp_train(site, debug=False):
    x, y = load_data(site)
    pipe_train(x, y, site, debug)

def temp_use(site):
    pass

if __name__ == '__main__':
    temp_train('my', True)
    pass
