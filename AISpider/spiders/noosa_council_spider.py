import re
import scrapy
import copy
import requests
from collections import OrderedDict
from scrapy import Request, Selector
from scrapy.http import HtmlResponse
from urllib.parse import urlencode
from datetime import datetime, date, timedelta
from common._string import except_blank
from common._date import get_all_month
import time
from common._date import get_all_month_
from common.set_date import get_this_month
from AISpider.items.noosa_council_items import NoosaCouncilItem
from bs4 import BeautifulSoup

class NoosaCouncilSpider(scrapy.Spider):
    """
    lockyer valley 的爬虫，原网站用.net开发，页面的渲染都在服务器完成，因此需要动态爬取，类似的需求还有
    """
    name = "noosa_council"
    allowed_domains = ["noo-web.t1cloud.com"]
    start_urls = [
        "https://noo-web.t1cloud.com/T1PRDefault/WebApps/eProperty/P1/eTrack/eTrackApplicationSearch.aspx"]
    USER_TYPE = 'P1.WEBGUEST'
    QUERY_TYPE = {'view': '$P1.ETR.RESULTS.VIW', 'query': '$P1.ETR.SEARCH.ENQ', 'appdet': '$P1.ETR.APPDET.VIW'}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br'
    }
    start_date = '19/08/1970'  # 网站最早的记录为 04/03/1991

    custom_settings = {
        # 'ITEM_PIPELINES': {
        #     "AISpider.pipelines.AispiderPipeline": None,
        # }
        'DOWNLOAD_DELAY': 3,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'LOG_STDOUT': True,
        #'LOG_FILE': 'scrapy_noosa_council.log',
        'DOWNLOAD_TIMEOUT': 1200
    }

    def __init__(self, run_type=None, days=30, *args, **kwargs):
        """
        run_type: 表示爬虫运行的类型， `all`代表爬取到当前日期的所有记录， `part`代表爬取部分
        days: 结合`run_type`一起使用， 当`run_type`不等于`all`,只爬取指定天数的数据默认为30天
        """
        super(NoosaCouncilSpider, self).__init__(*args, **kwargs)
        self.run_type = run_type
        if days == None:
            # 如果没有传days默认为这个月的数据
            self.days = get_this_month()
        else:
            now = datetime.now()
            days = int(days)
            date_from = (now - timedelta(days)).date().strftime('%d/%m/%Y')
            # 这里计算出开始时间 设置到self.days
            self.days = date_from
            self.now = datetime.now().date().strftime('%d/%m/%Y')
        self.cookie = None
        self.search_option = None

    def start_requests(self):
        """
        第一次请求，获取下一次请求的相关参数
        """
        for url in self.start_urls:
            url = self.get_url(url)
            self.update_cookie(url)
            # self.update_search_option(url)
            yield Request(url, dont_filter=True, headers=self.headers, cookies=self.cookie)

    def update_search_option(self, url):
        r = requests.get(url, headers=self.headers, cookies=self.cookie)
        respond = HtmlResponse(url, body=r.text, encoding='utf-8', request=r.request)
        self.search_option = respond.css(
            '#ctl00_Content_ddlApplicationType_elbList option::attr(value)').extract()
        self.search_option.remove('all')

    def get_url(self, url, is_query=True):
        q_params = dict(r=self.USER_TYPE)
        q_params['f'] = self.QUERY_TYPE['query'] if is_query else self.QUERY_TYPE['view']
        return '?'.join([url, urlencode(q_params)])

    def get_detail_url(self, appid):
        base_url = 'https://noo-web.t1cloud.com/T1PRDefault/WebApps/eProperty/P1/eTrack/eTrackApplicationDetails.aspx'
        q_params = dict(r=self.USER_TYPE)
        q_params['f'] = self.QUERY_TYPE['appdet']
        q_params['ApplicationId'] = appid
        return '?'.join([base_url, urlencode(q_params)])

    def get_paylod(self, response, page=None, date_from=None, date_to=None, search_class=None, search=True):
        params = OrderedDict()
        selector = Selector(text=response.text)
        params['__EVENTTARGET'] = 'ctl00$Content$btnSearch' \
            if search else \
            'ctl00$Content$cusResultsGrid$repWebGrid$ctl00$grdWebGridTabularView'
        if page:
            params['__EVENTARGUMENT'] = f'Page${page}'

        params['__VIEWSTATE'] = selector.css('#__VIEWSTATE::attr(value)').get()
        params['__VIEWSTATEGENERATOR'] = selector.css('#__VIEWSTATEGENERATOR::attr(value)').get()
        params['__SCROLLPOSITIONX'] = 0
        params['__SCROLLPOSITIONY'] = 226
        params['__EVENTVALIDATION'] = selector.css('#__EVENTVALIDATION::attr(value)').get()
        if date_from:
            params['ctl00$Content$txtDateFrom$txtText'] = date_from
        if date_to:
            params['ctl00$Content$txtDateTo$txtText'] = date_to
        if search_class:
            params['ctl00$Content$ddlApplicationType$elbList'] = search_class
        return urlencode(params)

    def parse(self, response):
        now = datetime.now()
        # for search_class in self.search_option:
        search_class = 'all'
        if self.run_type == 'all':
            all_month = get_all_month(self.start_date)
            # 修改获取数据方法，因为数据不能超过50页（50条），所以现在改为1个月获取一次
            # years = list(range(1991, now.year, 5))
            # years = [date(y, 1, 1) for y in years]
            for index, y_date in enumerate(all_month):
                if y_date == all_month:
                    break
                page = 1
                date_from = y_date
                date_to = all_month[index + 1]
                # 第一次请求
                # date_from = '28/01/2024'
                # date_to = '23/02/2024'
                # search_class = 'all'
                self.logger.info(f'date_from:{date_from}, date_to:{date_to}, search_class:{search_class}')
                payload = self.get_paylod(response, date_from=date_from, date_to=date_to, search_class=search_class)
                url = self.get_url(response.url.split('?')[0])
                headers = copy.copy(self.headers)
                headers |= {'Content-Type': 'application/x-www-form-urlencoded'}
                # 这块需要判断html请求是不是有数据，或者异常，所以不能使用scrapy.Request,因为yield 会让程序继续执行无法判断是否需要继续循环
                r = requests.post(url, data=payload, headers=headers, cookies=self.cookie)
                s_response = HtmlResponse(url=r.url, body=r.text, encoding='utf-8', request=r.request)
                if self.judge_error(s_response):
                    # 没找到相关记录
                    self.logger.info(
                        f'No Records. date_from:{date_from}, date_to:{date_to}, search_class:{search_class}')
                    continue
                # 判断是否超过爬取数据限制
                if self.judge_limit(s_response):
                    # 如果查询记录超过最大限制，打印，参数，之后重新请求
                    self.logger.error(
                        f'Result has been limit:date_from<{date_from}>, date_to<{date_to}>, search_class<{search_class}>')
                    continue
                for item in self.parse_grid(s_response):
                    yield item

                while True:
                    # 如果结果有分页， 在循环中获取其他页面
                    page += 1
                    payload = self.get_paylod(s_response, page=page, search=False)
                    url = self.get_url(s_response.url.split('?')[0], is_query=False)
                    headers = copy.copy(self.headers)
                    headers |= {'Content-Type': 'application/x-www-form-urlencoded'}
                    # 这块需要判断html请求是不是有数据，或者异常，所以不能使用scrapy.Request,因为yield 会让程序继续执行无法判断是否需要继续循环
                    r = requests.post(url, data=payload, headers=headers, cookies=self.cookie)
                    s_response = HtmlResponse(url=r.url, body=r.text, encoding='utf-8', request=r.request)
                    if self.judge_error(s_response):
                        # 分页结束，跳出循环
                        break
                    for item in self.parse_grid(s_response):
                        yield item
        else:
            page = 1
            date_from = self.days
            date_to = self.now
            payload = self.get_paylod(response, date_from=date_from, date_to=date_to, search_class=search_class)
            url = self.get_url(response.url.split('?')[0])
            headers = copy.copy(self.headers)
            headers |= {'Content-Type': 'application/x-www-form-urlencoded'}
            # 这块需要判断html请求是不是有数据，或者异常，所以不能使用scrapy.Request,因为yield 会让程序继续执行无法判断是否需要继续循环
            r = requests.post(url, data=payload, headers=headers, cookies=self.cookie)
            s_response = HtmlResponse(url=r.url, body=r.text, encoding='utf-8', request=r.request)
            if self.judge_error(s_response):
                # 没找到相关记录
                return
            if self.judge_limit(s_response):
                # 如果查询记录超过最大限制，打印，参数，之后重新请求
                self.logger.error(
                    f'Result has been limit:date_from<{date_from}>, date_to<{date_to}>, search_class<{search_class}>')
                return
            for item in self.parse_grid(s_response):
                yield item

            while True:
                # 如果结果有分页， 在循环中获取其他页面
                page += 1
                payload = self.get_paylod(s_response, page=page, search=False)
                url = self.get_url(s_response.url.split('?')[0], is_query=False)
                headers = copy.copy(self.headers)
                headers |= {'Content-Type': 'application/x-www-form-urlencoded'}
                # 这块需要判断html请求是不是有数据，或者异常，所以不能使用scrapy.Request,因为yield 会让程序继续执行无法判断是否需要继续循环
                r = requests.post(url, data=payload, headers=headers, cookies=self.cookie)
                s_response = HtmlResponse(url=r.url, body=r.text, encoding='utf-8', request=r.request)
                if self.judge_error(s_response):
                    # 分页结束，跳出循环
                    break
                for item in self.parse_grid(s_response):
                    yield item

    def judge_error(self, respond: HtmlResponse):
        """
        判断返回的页面是否有异常，有异常返回true，没有异常，返回False,简便处理，可扩展
        """
        title = respond.css('title::text').extract_first()
        if title and 'error' in title.lower():
            return True
        application_error = respond.css('#ctl00_Header_h1PageTitle::text').extract_first()
        error = respond.css('#ctl00_valErrors::text').extract_first()
        if error:
            error = except_blank([error])
        if error:
            error = error[0]
        error_info = respond.css('#ctl00_valErrors li::text').extract_first()
        if error or 'error' in application_error.lower():
            return True
        return False

    def judge_limit(self, respond: HtmlResponse):
        """
        判断返回的结果，是不是因为请求内容过多，被限制， 如果是返回True,否则返回False
        """
        limit_rows = respond.css('#ctl00_Content_cusResultsGrid_repWebGrid_ctl00_lblLimitedRows::text').extract_first()
        if limit_rows == 'Your results have been limited.':
            return True
        else:
            return False

    def parse_grid(self, respond: HtmlResponse):
        """
        解析表格页面
        ::修改，列表数据在详情页都有，所以将数据保存放到详情页
        """
        rows = respond.css('table.grid tr')
        for row in rows:
            # 原本html中没有a连接但是是通过document.write('<a href=\"javascript:__doPostBack(\'ctl00$Content$cusResultsGrid$repWebGrid$ctl00$grdWebGridTabularView\',\'Sort$RamId\')\">Application ID</a>');生成的因此匹配不到
            # 因此需要通过正则匹配
            if row.attrib.get('class') in ['headerRow', 'pagerRow', None]:
                continue

            row_items = row.css('td')
            app_no = re.search('>(.*)</a>', row_items[0].extract()).group(1)

            # 获取app详情页
            url = self.get_detail_url(appid=app_no)
            yield Request(url, dont_filter=True, callback=self.parse_detail,meta={'appid': app_no})

    def parse_detail(self, respond: HtmlResponse):

        item = NoosaCouncilItem()
        soup = BeautifulSoup(respond.text,'html.parser')
        # app 详情表格
        rows = respond.css(
            'div#ctl00_Content_cusPageComponents_repPageComponents_ctl00_cusPageComponentGrid_pnlCustomisationGrid table.grid tr')
        if rows:
            item['application_id'] = respond.meta['appid']
            item['application_type'] = '' if rows[1].css('td::text').extract()[1].isspace() else \
                rows[1].css('td::text').extract()[1]
            item['category'] = '' if rows[2].css('td::text').extract()[1].isspace() else \
                rows[2].css('td::text').extract()[1]
            item['description'] = '' if rows[3].css('td::text').extract()[1].isspace() else \
                rows[3].css('td::text').extract()[1]
            item['details'] = '' if rows[4].css('td::text').extract()[1].isspace() else \
                rows[4].css('td::text').extract()[1]
            # item['lodgement_date'] = '' if rows[5].css('td::text').extract()[1].isspace() else \
            #     rows[5].css('td::text').extract()[1]
            try:
                lodged_date = '' if rows[5].css('td::text').extract()[1].isspace() else \
                rows[5].css('td::text').extract()[1]
                time_array = time.strptime(lodged_date, '%d/%m/%Y')
                temp_data = int(time.mktime(time_array))
                item['lodgement_date'] = temp_data if lodged_date else 0  
            except:
                item['lodgement_date'] = 0
            item['decision'] = '' if rows[6].css('td::text').extract()[1].isspace() else \
                rows[6].css('td::text').extract()[1]
            item['officer'] = '' if rows[7].css('td::text').extract()[1].isspace() else \
                rows[7].css('td::text').extract()[1]

        # Properties
        rows = respond.css(
            'div#ctl00_Content_cusPageComponents_repPageComponents_ctl01_cusPageComponentGrid_pnlCustomisationGrid table.grid tr')
        if rows:
            item['property_id'] = soup.select_one('#ctl00_Content_cusPageComponents_repPageComponents_ctl01_cusPageComponentGrid_repWebGrid_ctl00_dtvWebGridListView_ctl02').get('value')
            item['address'] = '' if rows[1].css('td::text').extract()[1].isspace() else \
                rows[1].css('td::text').extract()[1]
            item['land_description'] = '' if rows[2].css('td::text').extract()[1].isspace() else \
                rows[2].css('td::text').extract()[1]

        # Names
        rows = respond.css(
            'div#ctl00_Content_cusPageComponents_repPageComponents_ctl02_cusPageComponentGrid_pnlCustomisationGrid table.grid tr')
        if rows:
            names = []
            for row in rows[1:]:
                names.append(':'.join(row.css("td::text").extract()))
            item['names'] = ','.join(names)

        # Document
        rows = respond.css(
            'div#ctl00_Content_cusPageComponents_repPageComponents_ctl04_cusPageComponentGrid_pnlNoRecords table.grid tr')
        if rows:
            documents = rows.css('td a::attr(href)').extract()
            documents = ['noo-web.t1cloud.com' + i for i in documents]
            item['documents'] = ';'.join(documents)
        del item['metadata']
        print(item)
        yield item

    def update_cookie(self, url):
        """
        做一次请求， 获取新的cookie
        """
        r = requests.get(url, headers=self.headers, allow_redirects=False)
        set_cookie = r.headers['Set-Cookie'].split(';')[0].split('=')
        self.cookie = {set_cookie[0]: set_cookie[1]}
