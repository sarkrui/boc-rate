'''
Author: Vincent Yang
Date: 2024-11-01 01:35:27
LastEditors: Vincent Yang
LastEditTime: 2024-11-01 02:04:22
FilePath: /boc-rate/boc-rate.py
Telegram: https://t.me/missuo
GitHub: https://github.com/missuo

Copyright © 2024 by Vincent, All Rights Reserved. 
'''

import httpx
from lxml import etree
from flask_cors import CORS
from flask_caching import Cache
from flask import Flask, jsonify, request

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
CORS(app)

currencyDict = {
    'AED': '阿联酋迪拉姆',
    'AUD': '澳大利亚元',
    'BRL': '巴西里亚尔',
    'CAD': '加拿大元',
    'CHF': '瑞士法郎',
    'DKK': '丹麦克朗',
    'EUR': '欧元',
    'GBP': '英镑',
    'HKD': '港币',
    'IDR': '印尼卢比',
    'INR': '印度卢比',
    'JPY': '日元',
    'KRW': '韩国元',
    'MOP': '澳门元',
    'MYR': '林吉特',
    'NOK': '挪威克朗',
    'NZD': '新西兰元',
    'PHP': '菲律宾比索',
    'RUB': '卢布',
    'SAR': '沙特里亚尔',
    'SEK': '瑞典克朗',
    'SGD': '新加坡元',
    'THB': '泰国铢',
    'TRY': '土耳其里拉',
    'TWD': '新台币',
    'USD': '美元',
    'ZAR': '南非兰特'
}

def get_exchange_rate(currency_code):
    url = "https://www.boc.cn/sourcedb/whpj/index.html"
    headers = {
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh-TW;q=0.7,zh;q=0.6",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Refer": "https://www.boc.cn/sourcedb/whpj/index_2.html",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd"
    }

    try:
        # Get and parse the page
        response = httpx.get(url=url, headers=headers)
        response.raise_for_status()
        tree = etree.HTML(response.content.decode('utf-8'))
        
        # Get all rows
        rows = tree.xpath('//table[@align="left"]/tr[position()>1]')
        
        # Find specified currency
        chinese_name = currencyDict.get(currency_code)
        if not chinese_name:
            return None
            
        # Find corresponding row
        for row in rows:
            currency_name = row.xpath('./td[1]/text()')[0].strip()
            if currency_name == chinese_name:
                # Extract data with additional calculations for middle prices
                foreign_exchange_buying_rate = row.xpath('./td[2]/text()')[0].strip() if row.xpath('./td[2]/text()') else ""
                cash_buying_rate = row.xpath('./td[3]/text()')[0].strip() if row.xpath('./td[3]/text()') else ""
                foreign_exchange_selling_rate = row.xpath('./td[4]/text()')[0].strip() if row.xpath('./td[4]/text()') else ""
                cash_selling_rate = row.xpath('./td[5]/text()')[0].strip() if row.xpath('./td[5]/text()') else ""
                boc_conversion_rate = row.xpath('./td[6]/text()')[0].strip() if row.xpath('./td[6]/text()') else ""

                try:
                    foreign_exchange_buying_rate = round(float(foreign_exchange_buying_rate), 2)
                    foreign_exchange_selling_rate = round(float(foreign_exchange_selling_rate), 2)
                    middle_price = round((foreign_exchange_buying_rate + foreign_exchange_selling_rate) / 2, 2)
                except ValueError:
                    middle_price = None

                try:
                    cash_buying_rate = round(float(cash_buying_rate), 2)
                    cash_selling_rate = round(float(cash_selling_rate), 2)
                    middle_cash_price = round((cash_buying_rate + cash_selling_rate) / 2, 2)
                except ValueError:
                    middle_cash_price = None

                try:
                    bocConversionRate = round(float(boc_conversion_rate), 2)
                except ValueError:
                    bocConversionRate = None

                # Construct data dictionary
                data = {
                    "data": [{
                        "currencyName": currency_code,
                        "foreignExchangeBuyingRate": foreign_exchange_buying_rate if foreign_exchange_buying_rate else "",
                        "cashBuyingRate": cash_buying_rate if cash_buying_rate else "",
                        "foreignExchangeSellingRate": foreign_exchange_selling_rate if foreign_exchange_selling_rate else "",
                        "cashSellingRate": cash_selling_rate if cash_selling_rate else "",
                        "middlePrice": middle_price if middle_price is not None else "",
                        "middleCashPrice": middle_cash_price if middle_cash_price is not None else "",
                        "bocConversionRate": bocConversionRate if bocConversionRate is not None else "",
                        "releaseTime": row.xpath('./td[7]/text()')[0].strip()
                    }]
                }
                return data

        return None
    
    except Exception as e:
        print(f"Error: {e}")
        return None

def cache_key():
    return request.url

@app.route('/')
@cache.cached(timeout=300, key_prefix=cache_key)
def get_rate():
    try:
        currency = request.args.get('currency', type=str)
        
        # Validate currency code
        if not currency or len(currency) != 3:
            return jsonify({
                "code": 400,
                "message": "Invalid currency code format. Please provide a 3-letter currency code.",
                "data": None
            }), 400
        
        currency = currency.upper()
        if currency not in currencyDict:
            return jsonify({
                "code": 400,
                "message": f"Unsupported currency code: {currency}",
                "data": None
            }), 400
            
        # Get exchange rate data
        result = get_exchange_rate(currency)
        
        if result and "data" in result:
            # Success case
            return jsonify({
                "code": 200,
                "message": "success",
                "data": result["data"]
            }), 200
            
        elif result and "error" in result:
            # External service error
            return jsonify({
                "code": 500,
                "message": result["error"],
                "data": None
            }), 500
        
        else:
            # Data not found
            return jsonify({
                "code": 404,
                "message": f"No exchange rate data found for currency: {currency}",
                "data": None
            }), 404

    except Exception as e:
        # Internal server error
        return jsonify({
            "code": 500,
            "message": f"Internal server error: {str(e)}",
            "data": None
        }), 500

if __name__ == '__main__':
    app.config['JSON_AS_ASCII'] = False
    app.run(host='0.0.0.0', port=6666)