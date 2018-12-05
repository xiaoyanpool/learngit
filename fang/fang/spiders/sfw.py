# -*- coding: utf-8 -*-
import scrapy
import re
from fang.items import *
from scrapy_redis.spiders import RedisSpider


class SfwSpider(RedisSpider):
    name = 'sfw'
    allowed_domains = ['fang.com']
    # start_urls = ['http://www.fang.com/SoufunFamily.htm']
    redis_key = "fang:start_urls"

    def parse(self, response):
        trs = response.xpath('//div[@class="outCont"]//tr')
        province = None
        for tr in trs:
            tds = tr.xpath('.//td[not(@class)]')
            province_td = tds[0]
            province_text = province_td.xpath('.//text()').get()
            province_text = re.sub(r'\s', '', province_text)
            if province_text:
                province = province_text
            # 不爬取海外城市的房源
            if province == '其它':
                continue
            city_td = tds[1]
            city_links = city_td.xpath('.//a')
            for city_link in city_links:
                city = city_link.xpath('.//text()').get()
                city_url = city_link.xpath('.//@href').get()
                # 构建新房的url链接
                url_module = city_url.split("//")
                scheme = url_module[0]
                domain = url_module[1]
                if 'bj.' in domain:
                    newhouse_url = 'http://newhouse.fang.com/house/s/'
                    esf_url = 'http://esf.fang.com/'
                else:
                    newhouse_url = scheme + '//' + 'newhouse.' + domain + 'house/s/'
                    # 构建二手房的url链接
                    esf_url = scheme + '//' + 'esf.' + domain
                # print('城市：%s%s' % (province, city))
                # print('新房链接:', newhouse_url)
                # print('二手房链接：', esf_url)

                yield scrapy.Request(url=newhouse_url, callback=self.parse_newhouse, meta={'info': (province, city)})

                yield scrapy.Request(url=esf_url, callback=self.parse_esf, meta={'info': (province, city)})
            #     break
            # break

    def parse_newhouse(self, response):
        province, city = response.meta.get('info')
        lis = response.xpath('//div[contains(@class, "nl_con")]/ul/li')
        for li in lis:
            name = li.xpath('.//div[@class="nlcd_name"]/a/text()').get()
            if name == None:
                continue
            else:
                name = name.strip()
                # print(name)

            house_type_list = li.xpath('.//div[contains(@class, "house_type ")]/a/text()').getall()
            house_type_list = list(map(lambda x: re.sub(r'\s', '', x), house_type_list))
            rooms = list(filter(lambda x: x.endswith('居'), house_type_list))
            area = ''.join(li.xpath('.//div[contains(@class, "house_type")]/text()').getall())
            area = re.sub(r'\s|－|/', '', area)
            address = li.xpath('.//div[@class="address"]/a/@title').get()
            district_text = ''.join(li.xpath('.//div[@class="address"]/a//text()').getall())
            district = re.search(r".*\[(.+)\].*", district_text).group(1)
            sale = li.xpath('.//div[contains(@class, "fangyuan")]/span/text()').get()
            price = "".join(li.xpath('.//div[@class="nhouse_price"]//text()').getall())
            price = re.sub(r'\s|广告', '', price)
            origin_url = li.xpath('.//div[@class="nlcd_name"]/a/@href').get()

            item = NewHouseItem(name=name, rooms=rooms, area=area, address=address, district=district, sale=sale, price=price, origin_url=origin_url, province=province, city=city)
            yield item
        next_url = response.xpath('//div[@class="page"]//a[@class="next"]/@href').get()
        if next_url:
            yield scrapy.Request(url=response.urljoin(next_url), callback=self.parse_newhouse, meta={'info': (province, city)})

    def parse_esf(self, response):
        province, city = response.meta.get('info')
        dls = response.xpath('//div[contains(@class, "shop_list")]/dl')
        for dl in dls:
            item = ESFHouseItem(province=province, city=city)
            name = dl.xpath('.//p[@class="add_shop"]/a/@title').get()
            if name == None:
                continue
            # print(name)
            infos = dl.xpath('.//p[@class="tel_shop"]/text()').getall()
            infos = list(map(lambda x: re.sub(r'\s', '', x), infos))
            for info in infos:
                if '厅' in info:
                    item['rooms'] = info
                elif '层' in info:
                    item['floor'] = info
                elif '向' in info:
                    item['toward'] = info
                elif '㎡' in info:
                    item['area'] = info
                elif '年' in info:
                    item['year'] = info
                # print(item)
            item['address'] = dl.xpath('.//p[@class="add_shop"]/span/text()').get()
            item['price'] = ''.join(dl.xpath('.//span[@class="red"]//text()').getall())
            item['unit'] = dl.xpath('.//dd[@class="price_right"]/span[2]/text()').get()
            detail_url = dl.xpath('.//dt[@class="floatl"]/a/@href').get()
            item['origin_url'] = response.urljoin(detail_url)
            # print(item['origin_url'])
            yield item
        next_url = response.xpath('//div[@class="page_al"]/p[1]/a/@href').get()
        yield scrapy.Request(url=response.urljoin(next_url), callback=self.parse_esf, meta={'info': (province, city)})







