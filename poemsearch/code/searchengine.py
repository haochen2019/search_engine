
import configparser
from distutils.command.config import config
import json
import jieba
import sqlite3
import re
from pypinyin import pinyin, lazy_pinyin, Style
import math
import operator

def is_balanced(query):
    brackets_b = query.count("(") == query.count(")")
    return brackets_b

def strip_brackets(query):
    count_left = 0
    for i in range(len(query) - 1):
        letter = query[i]
        if letter == "(":
            count_left += 1
        elif letter == ")":
            count_left -= 1
        if i > 0 and count_left == 0:
            return query

    if query[0] == "(" and query[-1] == ")":
        return query[1:-1]
    return query

class SearchEngine:
    stop_words = set()
    allDocs = {}
    config_path = ''
    config_encoding = ''
    pinyin_dict = {}
    N = 0
    K1 = 0
    B = 0
    AVG_L = 0

    def __init__(self, config_path, config_encoding):
        self.config_path = config_path
        self.config_encoding = config_encoding 
        config = configparser.ConfigParser()
        config.read(self.config_path, self.config_encoding) 
        f = open(config['DEFAULT']['stop_words_path'], encoding = config['DEFAULT']['stop_words_encoding'])
        words = f.read()
        self.stop_words = set(words.split('\n'))
        self.N = int(config['DEFAULT']['n'])
        self.K1 = float(config['DEFAULT']['k1'])
        self.B = float(config['DEFAULT']['b'])
        self.AVG_L = float(config['DEFAULT']['avg_l'])

        tf = open(config['DEFAULT']['docs_dict'])
        self.allDocs = json.load(tf,)
        self.conn = sqlite3.connect(config['DEFAULT']['db_path'])
    
    def clean_list(self, seg_list):
        cleaned_dict = {}
        n = 0
        for i in seg_list:
            i = i.strip().lower()
            if i != '' and i not in self.stop_words:
                n = n + 1
                if i in cleaned_dict:
                    cleaned_dict[i] = cleaned_dict[i] + 1
                else:
                    cleaned_dict[i] = 1
        return n, cleaned_dict

    def fetch_from_db(self, term):
        c = self.conn.cursor()
        c.execute('SELECT * FROM postings WHERE term=?', (term,))
        return(c.fetchone())
   
    def parse_query(self, query):
        if query[0] == '(' and query[-1] == ')':
            query = strip_brackets(query)
        match = []
        match_iter = re.finditer(r" (AND|OR) ", query, re.IGNORECASE)
        for m in match_iter:
            start = m.start(0)
            end = m.end(0)
            operator = query[start+1:end-1].lower()
            match_item = (start, end)
            match.append((operator, match_item))
        match_len = len(match)

        if match_len != 0:
            for i, (operator, (start, end)) in enumerate(match):
                left_part = query[:start]
                if not is_balanced(left_part):
                    continue

                right_part = query[end:]
                if not is_balanced(right_part):
                    raise ValueError("Query malformed")
                break

            if operator == "or":
                llist = set(self.parse_query(left_part))
                rlist = set(self.parse_query(right_part))
                return list(llist.union(rlist))
                # return list(set(self.parse_query(left_part)).union(set(self.parse_query(right_part))))
            elif operator == "and":
                llist = set(self.parse_query(left_part))
                rlist = set(self.parse_query(right_part))
                return list(llist.intersection(rlist))
                # return  list(set(self.parse_query(left_part)).intersection(set(self.parse_query(right_part))))
        else:
            return self.getDocid(query)

    def getDocid(self,term):
        Finalres = []
        res = []
        if term[:4] == "not ":
            Finalres = list(self.allDocs.keys())
            term = term[4:]
            seg_list = jieba.lcut(term, cut_all=False)
            n, cleaned_dict = self.clean_list(seg_list)
            for term in cleaned_dict.keys():
                r = self.fetch_from_db(term)
                if r is None:
                    continue
                else:
                    docs = r[2].split('\n')
                    for doc in docs:
                        docid, date_time, tf, ld = doc.split('\t')
                        res.append(docid)
            Finalres = list(set(Finalres) - set(res))
        else:
            r = self.fetch_from_db(term)
            seg_list = jieba.lcut(term, cut_all=False)
            n, cleaned_dict = self.clean_list(seg_list)
            for term in cleaned_dict.keys():
                if r is None:
                    continue
                docs = r[2].split('\n')
                for doc in docs:
                    docid, date_time, tf, ld = doc.split('\t')
                    res.append(docid)
            Finalres = res
        return Finalres
    
    def get_fuzzy_terms(self, wordList, resList,i, curWord):
        if i == len(wordList):
            resList.append(curWord)
            return
        for word in wordList[i]:
            self.get_fuzzy_terms(wordList, resList, i+1, curWord + word)

    def result_by_Boolean(self, query):
        res = self.parse_query(query.lower())
        if len(res) == 0:
            return 0,[]
        else:
            return 1, res
    
    def result_by_Zone_specific(self, author, dynasty,title, content):
        author_list = []
        dynasty_list = []
        title_list = []
        content_list = []
        res = []
        config = configparser.ConfigParser()
        config.read(self.config_path, self.config_encoding) 
        if author:#如果有作者限定
            file = config['DEFAULT']['doc_dir_path']
            f = open(file)
            fileData = json.load(f,)
            for poem in fileData:
                m_docid = poem["id"]
                m_docid = str(m_docid)
                if poem["author"] == author:
                    author_list.append(m_docid)
        else:
            author_list = list(self.allDocs.keys())

        if dynasty:
            file = config['DEFAULT']['doc_dir_path']
            f = open(file)
            fileData = json.load(f,)
            for poem in fileData:
                m_docid = poem["id"]
                m_docid = str(m_docid)
                if poem["dynasty"] == dynasty:
                    dynasty_list.append(m_docid)
        else:
            dynasty_list = list(self.allDocs.keys())

        _,title_list = self.result_by_Boolean(title)
        _,content_list = self.result_by_Boolean(content)

        res = list(set(author_list).intersection(set(dynasty_list)))
        res = list(set(res).intersection(set(title_list)))
        res = list(set(res).intersection(set(content_list)))
        if len(res) == 0:
            return 0,[]
        else:
            return 1, res

    def result_by_Fuzzy(self, query):
        # fuzzy搜索：返回包含与char读音（拼音和声调）相同的字的古诗
        path = "../data/characters_3500.txt"
        with open(path, "r", encoding="utf-8") as f:
            for line in f.readlines():
                ch = line.strip()
                ch_pinyin = pinyin(ch, style=Style.TONE3, heteronym=False)
                # heteronym 是否启用多音字模式
                for p_li in ch_pinyin:
                    for p in p_li:
                        if p not in self.pinyin_dict:
                            self.pinyin_dict[p] = [ch]
                        else:
                            self.pinyin_dict[p].append(ch)
        
        seg_list = jieba.lcut(query, cut_all=False)
        n, cleaned_dict = self.clean_list(seg_list)
        fuzzy_words = []
        for term in cleaned_dict.keys():
            ch_pinyin = pinyin(term, style=Style.TONE3, heteronym=False)
            wordList = []
            for p_li in ch_pinyin: #每个char
                for p in p_li: #四个音节
                    wordList.append(self.pinyin_dict[p])
            for i,words in enumerate(wordList):
                if term[i] not in words:
                    words.append(term[i])

            resList = []
            self.get_fuzzy_terms(wordList, resList, 0, '')
            
            fuzzy_words.extend(resList)

        fuzzy_words = list(set(fuzzy_words))

        # print(char_match)

        res = []
        for term in fuzzy_words:
            r = self.fetch_from_db(term)
            if r is None:
                continue
            docs = r[2].split('\n')
            for doc in docs:
                docid, date_time, tf, ld = doc.split('\t')
                res.append(docid)

        if len(res) == 0:
            return 0,[]
        else:
            return 1, res

    def result_by_rankBM25(self, query):
        seg_list = jieba.lcut(query, cut_all=False)
        n, cleaned_dict = self.clean_list(seg_list)
        BM25_scores = {}
        for term in cleaned_dict.keys():
            r = self.fetch_from_db(term)
            if r is None:
                continue
            df = r[1]
            w = math.log2((self.N - df + 0.5) / (df + 0.5))
            docs = r[2].split('\n')
            for doc in docs:
                docid, date_time, tf, ld = doc.split('\t')
                # docid = int(docid)
                tf = int(tf)
                ld = int(ld)
                s = (self.K1 * tf * w) / (tf + self.K1 * (1 - self.B + self.B * ld / self.AVG_L))
                if docid in BM25_scores:
                    BM25_scores[docid] = BM25_scores[docid] + s
                else:
                    BM25_scores[docid] = s
        BM25_scores = sorted(BM25_scores.items(), key = operator.itemgetter(1))
        BM25_scores.reverse()
        res = []
        for doc in BM25_scores:
            res.append(doc[0])
        if len(res) == 0:
            return 0, []
        else:
            return 1, res


if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(__file__))
    se = SearchEngine('../config.ini', 'utf-8')
    # flag, rs = se.result_by_Boolean("(NOT 巴) AND (郎行)")
    # flag, rs = se.result_by_Zone_specific('李白','唐','巴女', '词')
    # flag,rs = se.result_by_Fuzzy('郎行')
    flag,rs = se.result_by_rankBM25('词')
    print(rs[:10])
