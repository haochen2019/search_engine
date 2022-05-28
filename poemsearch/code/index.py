import configparser
from http.client import CONFLICT
from os import listdir
import json
import jieba
import os 
import sqlite3
class Doc:
    # 输出给倒排记录表项
    docid = 0
    title = ''
    tf = 0  # 词项频度
    ld = 0 #doc长度
    def __init__(self, docid,title, tf, ld):
        self.docid = docid
        self.title = title
        self.tf = tf
        self.ld = ld
    def __repr__(self) :
        return(str(self.docid) + '\t' + self.title + '\t' + str(self.tf) + '\t' + str(self.ld))
    def __str__(self):
        return(str(self.docid) + '\t' + self.title + '\t' + str(self.tf) + '\t' + str(self.ld))


class IndexModule:
    stop_words = set()
    posting_lists = {}
    docs = {}

    config_path = ''
    config_encoding = ''

    def __init__(self, config_path, config_encoding):
        self.config_path = config_path
        self.config_encoding = config_encoding
        config = configparser.ConfigParser()
        config.read(config_path, config_encoding)
        f = open(config['DEFAULT']['stop_words_path'], encoding=config['DEFAULT']['stop_words_encoding'])
        words = f.read()
        self.stop_words = set(words.split('\n'))

    def clean_dict(self, seg_list):
        clean_dict = {} #statistic the seg_list to get the terms dict(value is tf)
        length = 0
        for i in seg_list:
            i = i.strip().lower()
            if i != '' and i not in self.stop_words:
                length = length + 1
                if i in clean_dict:
                    clean_dict[i] = clean_dict[i] + 1
                else:
                    clean_dict[i] = 1
        return length, clean_dict 

    def write_postings_to_db(self, db_path):
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        c.execute('''DROP TABLE IF EXISTS postings''')
        c.execute('''CREATE TABLE postings
                     (term TEXT PRIMARY KEY, df INTEGER, docs TEXT)''')

        for key, value in self.posting_lists.items():
            doc_list = '\n'.join(map(str,value[1]))#将value[1]list的每个元素都进行map
            t = (key, value[0], doc_list)
            c.execute("INSERT INTO postings VALUES (?, ?, ?)", t)
        
        conn.commit()
        conn.close()
    def construct_postings_lists(self):
        config = configparser.ConfigParser()
        config.read(self.config_path,self.config_encoding)
        file = config['DEFAULT']['doc_dir_path']
        AVG_L = 0 # average document length

        f = open(file)
        fileData = json.load(f,)
        for poem in fileData:
            docid = poem["id"]
            title = poem["title"]
            self.docs[docid] = title

            author = poem["author"]
            dynasty = poem["dynasty"]
            content = poem["content"]
            translation = poem["translation"]
            annotation = poem["annotation"]
            appreciation = poem["appreciation"]
            background = poem["background"]

            # seg_list = jieba.lcut(title+'。'+content, cut_all=False)
            seg_list = jieba.lcut(title+'。'+content, cut_all=False)#采用精确模式：清华、华大
            ld, cleaned_dict = self.clean_dict(seg_list)

            AVG_L = AVG_L + ld # all docs length

            for term, tf in cleaned_dict.items():
                d = Doc(docid, title,tf, ld)
                if term in self.posting_lists:
                    self.posting_lists[term][0] = self.posting_lists[term][0] + 1#df
                    self.posting_lists[term][1].append(d)
                else:
                    self.posting_lists[term] = [1, [d]]
        doc_dict = config['DEFAULT']['docs_dict']
        with open(doc_dict, "w", encoding=self.config_encoding) as ff:
            json.dump(self.docs, ff,ensure_ascii=False)
        AVG_L = AVG_L / len(fileData)
        config.set('DEFAULT', 'N', str(len(fileData)))
        config.set('DEFAULT', 'avg_l', str(AVG_L))
        with open(self.config_path, 'w', encoding = self.config_encoding) as configfile:
            config.write(configfile)
        self.write_postings_to_db(config['DEFAULT']['db_path'])

if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    im = IndexModule('../config.ini', 'utf-8')
    im.construct_postings_lists()
            
