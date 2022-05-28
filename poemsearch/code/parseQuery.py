import re

def getDocid(term):
    r = self.fetch_from_db(term)
    res = []
    if r is None:
        return []
    df = r[1]
    docs = r[2].split('\n')
    for doc in docs:
        docid, date_time, tf, ld = doc.split('\t')
        docid = int(docid)
        res.append(docid)
    return res

    
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
            return list(set(parse_query(left_part)).union(set(parse_query(right_part))))
        elif operator == "and":
            return  list(set(parse_query(left_part)).intersection(set(parse_query(right_part))))
    else:
        return getDocid(query)
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