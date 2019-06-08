import re
import jieba
import jieba.analyse
import fp_growth_py3 as fp

def split_into_word(article, output='list'):
    """
    Split an article into words.

    :param article: an article in string data type
    :return: a word list, type='list'
    """
    jieba.set_dictionary('C:\\Program Files\\Python36\\Lib\\site-packages\\jieba\\dict.txt.big')  # 切換為繁體詞庫
    seg_list = jieba.cut(article, cut_all=False)  # 精確模式
    # seg_list = jieba.cut_for_search(article)  # 搜索引擎模式
    if output == 'list':
        return seg_list
    elif output == 'str':
        seg = ''
        for i in seg_list:
            seg += (i + ' ')
        seg = re.sub(r'(\s*，\s*)', '，', seg)
        return seg


def text2trans(text):
    trans = []
    for item in text.split('，'):
        if item:
            trans.append(item.split())
    return trans


# remove stop words
def clean(trans, sw_path):
    sw_dict = {}
    clean_trans = []
    l = []
    with open(sw_path, 'r', encoding='UTF-8') as f:
        for line in f.readlines():
            sw_dict[line.strip()] = True
    for tran in trans:
        for t in tran:
            if t not in sw_dict:
                l.append(t)
        if l:
            clean_trans.append(l)
        l = []
    return clean_trans


def rm_dup(trans):
    """
    Remove duplicate words in a sentence.
    Duplicate words will cause the FPGrowth run unexpectedly.
    """
    l = []
    for tran in trans:
        temp = set()
        for word in tran:
            if word not in temp:
                temp.add(word)
        l.append(temp)
    return l   # l: [{'a', 'b', 'c'}, {'dd, 'ff'}, {'haha', 'eee'}]


def convert(s):
    l = []
    for item in s.split():
        l.append([item])
    return l


def rm_stop_words(word_list, sw_path, output='list'):
    sw_dict = {}
    l = []
    s = ''
    with open(sw_path, 'r', encoding='UTF-8') as f:
        for line in f.readlines():
            sw_dict[line.strip()] = True
    for w in word_list:
        if w not in sw_dict:
            l.append(w)
            s += (w + ' ')
    if output == 'list':
        return l
    elif output == 'str':
        return s


def food_dict(filename):
    food = {}
    with open(filename, 'r', encoding='UTF-8') as f:
        for line in f.readlines():
            if '#' not in line:
                food[line.strip('\n\t')] = True
    return food


def find_food(word_list, food):
    result = {}
    for pat_list, sup in word_list:
        pat = ''.join(pat_list)
        for w in pat_list:
            if w in food and pat not in result:
                result[pat] = sup
    return result


def sort(word_list):
    # [(['aaa'], 10), (['bbb'], 14)]
    sorted_list = []
    for item in word_list:
        sorted_list.append([sorted(item[0]), item[1]])
    return sorted(sorted_list, key=lambda item: item[1], reverse=True)


def input(filename):
    with open(filename, 'r', encoding='UTF-8') as f:
        s = f.read()
        return s


def output(word_list, filename):
    with open(filename, 'w', encoding='UTF-8') as f:
        for pat, sup in word_list:
        # for pat, sup in word_list:
            f.write(''.join(pat) + ' ' + str(sup) + '\n')


def output_result(result, filename):
    with open(filename, 'w', encoding='UTF-8') as f:
        for k, v in result.items():  # result is in type dictionary
            f.write(k + ' ' + str(v) + '\n')


if __name__ == '__main__':

    print('Reading input file...')
    articles = input('台南 美食.txt')

    print('Splitting...')
    s = split_into_word(articles, 'str')

    print('Converting to transactions...')
    trans = text2trans(s)

    sw_path = 'C:\\Program Files\\Python36\\Lib\\site-packages\\jieba\\stop_words2.txt'  # stop_words2.txt might be better
    print('Cleaning symbols...')
    # trans = clean(trans, sw_path)  # remove stop words
    trans = rm_dup(trans)

    print('Finding frequent patterns...')
    fp = fp.find_frequent_itemsets(trans, 2, True)
    fp = sort(fp)  # sort by support

    food = food_dict('food_list.txt')
    result = find_food(fp, food)   # return's a dictionary


    print('Writing output file...')
    output(fp, 'fp台南.txt')
    output_result(result, 'fp台南(only food).txt')
    

    print('Done!')