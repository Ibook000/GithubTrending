import yaml

try:
    with open('.github/workflows/generate_trending.yml', 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    print('✅ YAML格式验证通过！')
    print(f'文件包含 {len(data)} 个顶层元素')
except yaml.YAMLError as e:
    print('❌ YAML验证失败:')
    print(str(e))
except FileNotFoundError:
    print('❌ 文件未找到')
except Exception as e:
    print('❌ 验证过程中发生错误:')
    print(str(e))