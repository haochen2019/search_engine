from asyncio import FastChildWatcher
import math
from nis import match
import re

class Binary:
    def __init__(self, left, right):
        self.left = left
        self.right = right

class AND(Binary):
    def evaluate(self, doc):
        left_match = self.left.evaluate(doc)
        if not left_match:
            return False
        right_match = self.right.evaluate(doc)
        if not right_match:
            return False
        return True
    def __repr__(self):
        return f"({self.left}) AND ({self.right})"

class OR(Binary):
    def evaluate(self, doc):
        if self.left.evaluate(doc):
            return True
        if self.right.evaluate(doc):
            return True
        return False

    def __repr__(self):
        return f"({self.left}) OR ({self.right})"

class Entry:
    def __init__(self, query):
        self.not_ = False
        if query[:4] == "not ":
            self.not_ = True
            query = query[4:]
        self.query = query
    def evaluate(self, doc):
        res = self.query in doc
        if self.not_:
            return not res
        return res
    def __repr__(self):
        if self.not_:
            return f'NOT "{self.query}"'
        return f'"{self.query}"'   

class Query:
    def __init__(self, query):
        self.query = parse_query(query.lower())
    def evaluate(self, doc):
        return self.query.evaluate(doc)
    def filter(self, documents):
        docs = []
        for doc in documents:
            if not self.evaluate(doc):
                continue
            docs.append(doc)
        return docs

def parse_query(query):
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
            return OR(
                parse_query(left_part),
                parse_query(right_part)
            )
        elif operator == "and":
            return AND(
                parse_query(left_part),
                parse_query(right_part)
            )
    else:
        return Entry(query)
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

if __name__ == "__main__":
    documents = [
    "巴地的长江水，急湍奔流快如箭，巴水上的船儿顺水漂流疾若飞",
    "Frodo is the main character in The Lord of the Rings",
    "Ian McKellen interpreted Gandalf in Peter Jackson's movies",
    "Elijah Wood was cast as Frodo Baggins in Jackson's adaptation",
    "The Lord of the Rings is an epic fantasy novel by J. R. R. Tolkien"]
    eldar = Query('(巴 OR 吃) AND (长江)')
    print(eldar.filter(documents))
