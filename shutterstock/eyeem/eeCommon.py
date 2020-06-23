import urllib.parse

DEFAULT_HEADERS = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0',
                                      'Connection':'keep-alive',
                                      "Accept":'application/json',
                                      'Accept-Encoding':'gzip, deflate, br',
                                      'Accept-Language':'en-US,en;q=0.5',
                                      'X-Requested-With': 'XMLHttpRequest',
                   #                    'Origin': 'https://www.eyeem.com',
                   # 'Referer':'https://www.eyeem.com/upload',
                   # 'Host':'www.eyeem.com',
                   # 'Cache-Control':'no-cache',
                   # 'Access-Control-Allow-Credentials':'true',
                   # 'Access-Control-Allow-Headers':'Content-Type, X-Requested-With, X-PINGOTHER, X-File-Name, Cache-Control',
                   # 'Access-Control-Allow-Methods':'PUT, POST, GET, OPTIONS',
                   # 'Access-Control-Allow-Origin':'*',
                   }

cookie_dict = {}
categories = None
reasons = None



def ee_login():
    global categories
    global reasons

    # cookies = os.environ['SS_AUTO_LOGIN_COOKIES']
    # cookies acquired on 17.05.2020
    # cookies = 'connect.sid=s%3AWZXAY-aGBgSfeiHgHQvY8k_hDZbi0gmK.yfqAhUlfRILvts7LiBr%2B0LZ%2BJXhiHGVv1yS3ZMVVYnI'
    # cookies = 'AWSALB=xbNothC09lLIqtLdXiOjRmwN78Q28pujUI3Qva2xsq/EaUQlgAeuUAZDz4lCY0qvN5rmwt71CrlpBi55ygMsTsVFCFM42rPF2AemGEG2ZcvJ5dphJYQ1sQIkHHA7; AWSALBCORS=xbNothC09lLIqtLdXiOjRmwN78Q28pujUI3Qva2xsq/EaUQlgAeuUAZDz4lCY0qvN5rmwt71CrlpBi55ygMsTsVFCFM42rPF2AemGEG2ZcvJ5dphJYQ1sQIkHHA7; connect.sid=s%3A1TV5dmIG4gsER0sXTnstpGx3mZLdh_lW.UQbdZ0IK7JlRNkgUOMn7%2FCIVvFM0Ny7DjbSEgvH0DaU'
    cookies = 'connect.sid=s%3Am-sIAYkhLHqzeqCsJ2FtpjzxzkxJlZyh.EpkE7giUgQEaQB2Zq6vz4q1eDsVnLNOn3VWlarSo5vg'
    cookies = urllib.parse.unquote(cookies)

    for c in cookies.split(';'):
        name,val = c.split('=',1)
        cookie_dict[name.strip()] = val.strip()


