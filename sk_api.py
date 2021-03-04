from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.naive_bayes import MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import SGDClassifier
from sklearn import metrics
from shopee_api import mydb
import time, numpy, joblib

def load_data():
    sql = "select distinct name, category_id from items where account like '%my' and category_id in (select category_id from (select count (category_id) as num, category_id from items group by category_id) where num > 50)"
    #sql = "select name, cat from temp"
    con = mydb(sql)
    print('loaded ', len(con), time.ctime())
    x, y = [i[0] for i in con], [i[1].split(".")[-1] for i in con]
    return (x, y)

def pp_train(x, y, model_name, debug=False):
    if debug:
        x_train, x_test, y_train, y_test = train_test_split(x, y, stratify=y, random_state=12)
    else:
        x_train,y_train = x, y
    model = make_pipeline(
    CountVectorizer(),
    TfidfTransformer(),
    #MultinomialNB(),
    SGDClassifier(loss='hinge', penalty='l2',alpha=1e-3, random_state=42, max_iter=5, tol=None),
    )

    model.fit(x_train, y_train)
    joblib.dump(model, model_name)
    print('saved', time.ctime())
    if debug:
        predicted = model.predict(x_test)
        print('predicted', time.ctime())
        print(numpy.mean(predicted == y_test))

def pp_predict(x_test, model_name):
    model = joblib.load(model_name)
    predicted = model.predict(x_test)
    data = list(zip(x_test, predicted))
    return data

if __name__ == "__main__":
    x, y = load_data()
    pp_train(x, y, 'd://model_my_train.joblib', debug=True)
