import requests
import json

login_resp = requests.post(
    'http://localhost:8099/api/login',
    data={'username': 'admin', 'password': 'admin123'}
)
token = login_resp.json()['access_token']
print('登录成功，token 长度:', len(token))

headers = {'Authorization': f'Bearer {token}'}
stats_resp = requests.get(
    'http://localhost:8099/api/audit-statistics',
    headers=headers,
    params={'days': 7}
)
print('状态码:', stats_resp.status_code)
if stats_resp.status_code == 200:
    stats = stats_resp.json()
    print('统计接口调用成功!')
    print('总查询次数:', stats['total_queries'])
    print('成功执行:', stats['success_queries'])
    print('风险拦截:', stats['blocked_queries'])
    print('执行失败:', stats['failed_queries'])
    print('查询趋势天数:', len(stats['query_trend']))
    print('风险分布项数:', len(stats['risk_distribution']))
    print('Top用户数:', len(stats['top_users']))
    print('数据源统计数:', len(stats['datasource_stats']))
    print('\n查询趋势数据:')
    for item in stats['query_trend']:
        print(f'  {item["date"]}: {item["count"]} 次')
    print('\n风险分布:')
    for item in stats['risk_distribution']:
        print(f'  {item["name"]}: {item["value"]}')
    print('\nTop用户:')
    for item in stats['top_users']:
        print(f'  {item["username"]}: {item["count"]} 次')
    print('\n数据源统计:')
    for item in stats['datasource_stats']:
        print(f'  {item["name"]}: {item["count"]} 次')
else:
    print('错误响应:', stats_resp.text)
