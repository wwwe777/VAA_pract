import requests
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
from datetime import datetime

BASE_URL = 'https://finance.naver.com/sise/sise_market_sum.nhn?sosok='
CODES = [0, 1] # KOSPI:0 , KOSDAQ:1
START_PAGE = 1
fields = []
now = datetime.now()
formattedDate = now.strftime("%Y%m%d")


def execute_crawler():
    #데이터 크롤링 고고싱
    df_total = [] # KOSPI, KOSDAQ 종목을 하나로 합치는데 사용할 변수

    for code in CODES: # CODES에 담긴 KOSPI, KOSDAQ 종목 모두를 크롤링하려고 for 문 사용

        res = requests.get(BASE_URL + str(CODES[0])) # 코스피 total_page 를 가져오는 requests
        page_soup = BeautifulSoup(res.text, 'lxml')

        # '맨뒤'에 해당하는 태그를 기준으로 전체 페이지 수 추출
        total_page_num = page_soup.select_one('td.pgRR > a')
        total_page_num = int(total_page_num.get('href').split('=')[-1]) #구분자 = 을기준으로 리스트의 맨마지막 요소 추출
        # 조회할 수 있는 항목 항목 종류 추출(위에 체크하는거)
        ipt_html = page_soup.select_one('div.subcnt_sise_item_top')

        # 전역볍수 fields에 항목들을 담아 다른 함수에서도 접근 가능하도록 만듬
        global fields
        fields = [item.get('value') for item in ipt_html.select('input')]  # 조회가능 항목 리스트 추출

        # page마다 존재하는 모든 종목들의 항목정보를 크롤링해서 result에 저장(여기서 crawler 함수가 한 페이씩 크롤링해오는 역할을 담당)
        result = [crawler(code, str(page)) for page in range(1, total_page_num + 1)]

        #페이지마다 존재하는 모든 종목의 항목 정보를 크롤링 해서 result에 저장 ( 여기서 crawler 함수가 한 페이지씩 크롤링 해 오는 역할 담당)
        df = pd.concat(result, axis=0, ignore_index=True)

        # df변수는 KOSPI, KOSDAQ별로 크롤링한 종목 정보고, 이를 하나로 합치고자 df_total에 추가
        df_total.append(df)

    # df_total을 하나의 데이터프레일으로 만듬
    df_total = pd.concat(df_total)

    # 합친 데이터 프레임의 index 번호를 새로 매김
    df_total.reset_index(inplace=True, drop=True)

    df_total.to_excel('NaverFinance.xlsx') # 전체 크롤링 결과를 엑셀로 출력

    return df_total


def crawler(code, page):
    global fields

    # Naver Finance에 전달한 값들 세팅(요청을 보낼 때는 menu, fields, returnURL을 지정해서 보내야 함)
    data = {'menu': 'market_sum',
            'fieldIds': fields,
            'returnUrl': BASE_URL + str(code) + "&page=" + str(page)}

    # 네이버 요청을 전달(post방식)
    res = requests.post('https://finance.naver.com/sise/field_submit.nhn', data=data)

    page_soup = BeautifulSoup(res.text, 'lxml')

    # 크롤링 할 table의 html을 가져오는 코드( 크롤링 대상 요소의 클래스는 웹 브라우저에서 확인
    table_html = page_soup.select_one('div.box_type_l')

    # [1:-1] --> column 이름을 가공함
    header_data = [item.get_text().strip() for item in table_html.select('thead th')][
                  1:-1]  # 하위는 그냥 띄어쓰기 한다 like 'thead th' [1:-1] 은 맨처음(Num#), 맨마지막(토론식) 제외시키는 필터역할

    ''' 함수공부 !
    lambda는 함수 선언 함수 !
    e.g. 

    func_a = lambda x: x**3 #  'lambda 인수 : 리턴값' 구조 
    a = func_a(2) --> a = 8

    아래 함수와 동일

    def func_a(x):
        return x**3 
        '''
    # 종목명 + 수치 추출(a.title = 종목명, td.number = 기타수치) , find_all 함수에서 인수가 lambda x 의 x에 들어가서 : 이후에 나오는 리턴값으로 리턴!
    inner_data = [item.get_text().strip() for item in table_html.find_all(lambda x:
                                                                          (x.name == 'a' and
                                                                           'tltle' in x.get('class', [])) or
                                                                          (x.name == 'td' and
                                                                           'number' in x.get('class', []))
                                                                          )]
    no_data = [item.get_text().strip() for item in table_html.select('td.no')]  # 페이지마다 있는 종목의 순번 가져오기
    number_data = np.array(inner_data)  # 리스트 데이터인 no_data 를 행열(array)로 바꿈

    number_data.resize(len(no_data), len(header_data))  # 가로 x 세로 크기에 맞게 행렬화

    # 한페이지에서 얻은 정모를 모아 데이터프레임으로 만들어 변환
    df = pd.DataFrame(data=number_data, columns=header_data)
    return df


execute_crawler()