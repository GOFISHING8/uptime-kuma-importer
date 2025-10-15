from flask import Flask, render_template, request, jsonify
import pandas as pd
from uptime_kuma_api import UptimeKumaApi
import os
import sys
from werkzeug.utils import secure_filename
import traceback
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_api_connection(kuma_url, username, password):
    """创建Uptime Kuma API连接"""
    try:
        api = UptimeKumaApi(kuma_url)
        api.login(username, password)
        return api, None
    except Exception as e:
        return None, f"API连接失败: {str(e)}"

def clean_nan_values(data):
    """递归清理数据中的NaN值，将其转换为None"""
    if isinstance(data, dict):
        return {k: clean_nan_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_nan_values(item) for item in data]
    elif isinstance(data, float) and pd.isna(data):
        return None
    else:
        return data

class CustomJSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理NaN值"""
    def default(self, obj):
        if isinstance(obj, float) and pd.isna(obj):
            return None
        return super().default(obj)

app.json_encoder = CustomJSONEncoder

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-monitors', methods=['POST'])
def get_monitors():
    """获取所有监控项列表"""
    data = request.json
    kuma_url = data.get('kuma_url', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not all([kuma_url, username, password]):
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        # 建立API连接
        api, error = get_api_connection(kuma_url, username, password)
        if error:
            return jsonify({'error': error}), 400
        
        # 获取所有监控项
        monitors = api.get_monitors()

        # 为每个监控项添加标签信息
        for monitor in monitors:
            #确保ID是字符串类型
            monitor['id_str'] = str(monitor.get('id', ''))
            # 添加空的标签名称字段
            monitor['tag_names'] = ''

        
        # 关闭API连接
        api.disconnect()
        
        return jsonify({
            'success': True,
            'monitors': monitors,
            'total': len(monitors)
        })
        
    except Exception as e:
        print(f"获取监控项失败: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({'error': f'获取监控项失败: {str(e)}'}), 500

@app.route('/delete-monitors', methods=['POST'])
def delete_monitors():
    """批量删除监控项"""
    data = request.json
    monitor_ids = data.get('monitor_ids', [])
    kuma_url = data.get('kuma_url', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not all([monitor_ids, kuma_url, username, password]):
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        # 建立API连接
        api, error = get_api_connection(kuma_url, username, password)
        if error:
            return jsonify({'error': error}), 400
        
        results = {
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        # 批量删除监控项
        for monitor_id in monitor_ids:
            try:
                monitor_id_int = int(monitor_id)
                api.delete_monitor(monitor_id_int)
                results['success'] += 1
                print(f"成功删除监控项 ID: {monitor_id_int}")
            except Exception as e:
                error_msg = f"删除监控项 {monitor_id} 失败: {str(e)}"
                results['failed'] += 1
                results['errors'].append(error_msg)
                print(f"删除失败: {error_msg}")
        
        # 关闭API连接
        api.disconnect()
        
        return jsonify({
            'success': True,
            'results': results,
            'message': f'删除完成！成功: {results["success"]}, 失败: {results["failed"]}'
        })
        
    except Exception as e:
        return jsonify({'error': f'删除过程中发生错误: {str(e)}'}), 500

@app.route('/delete-by-filter', methods=['POST'])
def delete_by_filter():
    """根据条件筛选并删除监控项"""
    data = request.json
    kuma_url = data.get('kuma_url', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    filters = data.get('filters', {})
    
    if not all([kuma_url, username, password]):
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        # 建立API连接
        api, error = get_api_connection(kuma_url, username, password)
        if error:
            return jsonify({'error': error}), 400
        
        # 获取所有监控项
        all_monitors = api.get_monitors()
        
        # 应用筛选条件
        filtered_monitors = []
        for monitor in all_monitors:
            match = True
            
            # 名称筛选
            if filters.get('name_filter') and filters.get('name_keyword'):
                keyword = filters['name_keyword'].lower()
                if filters['name_filter'] == 'contains':
                    if keyword not in monitor['name'].lower():
                        match = False
                elif filters['name_filter'] == 'starts_with':
                    if not monitor['name'].lower().startswith(keyword):
                        match = False
                elif filters['name_filter'] == 'ends_with':
                    if not monitor['name'].lower().endswith(keyword):
                        match = False
            
            # 类型筛选
            if filters.get('type_filter') and filters['type_filter'] != 'all':
                if monitor['type'] != filters['type_filter']:
                    match = False
            
            if match:
                filtered_monitors.append(monitor)
        
        results = {
            'success': 0,
            'failed': 0,
            'errors': [],
            'matched_count': len(filtered_monitors)
        }
        
        # 删除匹配的监控项
        for monitor in filtered_monitors:
            try:
                api.delete_monitor(monitor['id'])
                results['success'] += 1
            except Exception as e:
                error_msg = f"删除监控项 {monitor['name']} ({monitor['id']}) 失败: {str(e)}"
                results['failed'] += 1
                results['errors'].append(error_msg)
        
        # 关闭API连接
        api.disconnect()
        
        return jsonify({
            'success': True,
            'results': results,
            'message': f'找到 {results["matched_count"]} 个匹配项，删除完成！成功: {results["success"]}, 失败: {results["failed"]}'
        })
        
    except Exception as e:
        return jsonify({'error': f'删除过程中发生错误: {str(e)}'}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    """上传并预览CSV文件"""
    if 'file' not in request.files:
        return jsonify({'error': '没有选择文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # 尝试不同编码读取CSV
            try:
                df = pd.read_csv(filepath, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(filepath, encoding='gbk')
                except:
                    df = pd.read_csv(filepath, encoding='latin-1')
            
            # 清理NaN值
            df = df.fillna('')  # 将NaN替换为空字符串
            preview_data = df.head(10).replace({pd.NaT: None}).to_dict('records')
            columns = list(df.columns)
            
            # 清理数据中的NaN值
            preview_data_cleaned = clean_nan_values(preview_data)
            
            return jsonify({
                'success': True,
                'filename': filename,
                'preview': preview_data_cleaned,
                'columns': columns,
                'total_rows': len(df)
            })
            
        except Exception as e:
            return jsonify({'error': f'读取CSV文件失败: {str(e)}'}), 400
    
    return jsonify({'error': '不支持的文件类型，请上传CSV文件'}), 400

@app.route('/import', methods=['POST'])
def import_monitors():
    """批量导入监控项"""
    data = request.json
    filename = data.get('filename')
    kuma_url = data.get('kuma_url', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not all([filename, kuma_url, username, password]):
        return jsonify({'error': '缺少必要参数'}), 400
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': '文件不存在'}), 400
    
    try:
        # 建立API连接
        api, error = get_api_connection(kuma_url, username, password)
        if error:
            return jsonify({'error': error}), 400
        
        # 读取CSV文件并清理NaN值
        try:
            df = pd.read_csv(filepath, encoding='utf-8')
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(filepath, encoding='gbk')
            except:
                df = pd.read_csv(filepath, encoding='latin-1')
        
        # 清理NaN值，将其替换为None或空字符串
        df = df.fillna('')  # 将所有NaN替换为空字符串
        monitors = df.replace({pd.NaT: None}).to_dict('records')
        
        # 再次清理数据中的NaN值
        monitors_cleaned = clean_nan_values(monitors)
        
        total = len(monitors_cleaned)
        
        results = {
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        # 第一步：准备标签
        tag_id_map = {}
        print("开始准备标签...")
        for field_name in ['sysname', 'appname', 'hostinfo']:
            for monitor in monitors_cleaned:
                value = monitor.get(field_name)
                if not value:
                    continue
                if value in tag_id_map:
                    continue
                
                try:
                    existing_tags = api.get_tags()
                    tag_id = next((t['id'] for t in existing_tags if t['name'] == value), None)
                    if tag_id is None:
                        color = "gray"
                        tag_data = api.add_tag(name=value, color=color)
                        tag_id = tag_data['id']
                    tag_id_map[value] = tag_id
                except Exception as e:
                    error_msg = f"创建/获取标签失败: {value} - {str(e)}"
                    results['errors'].append(error_msg)
        
        # 第二步：导入监控项并绑定标签
        print(f"开始导入 {total} 个监控项...")
        for idx, monitor in enumerate(monitors_cleaned, 1):
            name = monitor.get('name', f'Unnamed-{idx}')
            
            try:
                # 确保数值类型的字段是整数而不是字符串
                monitor_data = monitor.copy()
                for key in ['interval', 'retryInterval', 'maxretries', 'port']:
                    if key in monitor_data and monitor_data[key]:
                        try:
                            monitor_data[key] = int(monitor_data[key])
                        except (ValueError, TypeError):
                            monitor_data[key] = None
                
                # 创建监控项
                monitor_args = {
                        'name': monitor_data.get('name'),
                        'type': monitor_data.get('type'),
                        'interval': monitor_data.get('interval', 60),
                        'retryInterval': monitor_data.get('retryInterval', 30),
                        'maxretries': monitor_data.get('maxretries', 3),
                        'description': monitor_data.get('description'),
                }
                
                # 根据监控类型添加特定参数
                monitor_type = monitor_data.get('type')
                if monitor_type in ['http', 'https']:
                    monitor_args['url'] = monitor_data.get('url')
                elif monitor_type in ['port', 'tcp', 'udp']:
                    monitor_args['hostname'] = monitor_data.get('hostname') or monitor_data.get('url')
                    port_value = monitor_data.get('port')
                    if port_value:
                        try:
                            monitor_args['port'] = int(port_value)
                        except (ValueError, TypeError):
                            print(f"警告: 端口号格式错误: {port_value}")
                elif monitor_type == 'ping':
                    monitor_args['hostname'] = monitor_data.get('hostname') or monitor_data.get('url')
                elif monitor_type == 'dns':
                    monitor_args['dns_resolve_server'] = monitor_data.get('dns_resolve_server', 'cloudflare')
                    monitor_args['dns_resolve_type'] = monitor_data.get('dns_resolve_type', 'A')
                    monitor_args['hostname'] = monitor_data.get('hostname') or monitor_data.get('url')
                optional_params = ['weight_threshold', 'expiryNotification', 'ignoreTls', 'maxredirects']
                for param in optional_params:
                    if param in monitor_data and monitor_data[param] is not None:
                        monitor_args[param] = monitor_data[param]

                result = api.add_monitor(**monitor_args)

                # 获取monitor_id
                monitor_id = result.get('id') or result.get('monitorID')
                if not monitor_id:
                    raise Exception(f"无法获取monitor_id，返回结果: {result}")
                
                # 绑定标签
                for field in ['sysname', 'appname', 'hostinfo']:
                    value = monitor_data.get(field)
                    if value and value in tag_id_map:
                        tag_id = tag_id_map[value]
                        try:
                            api.add_monitor_tag(monitor_id=monitor_id, tag_id=tag_id)
                        except Exception as e:
                            error_msg = f"监控项 '{name}' 绑定标签失败: {value} - {str(e)}"
                            results['errors'].append(error_msg)
                
                results['success'] += 1
                
            except Exception as e:
                error_msg = f"导入失败 {idx}/{total}: {name} - {str(e)}"
                results['failed'] += 1
                results['errors'].append(error_msg)
                print(f"错误详情: {traceback.format_exc()}")
        
        # 关闭API连接
        api.disconnect()
        
        # 清理上传的文件
        try:
            os.remove(filepath)
        except:
            pass
        
        return jsonify({
            'success': True,
            'results': results,
            'message': f'导入完成！成功: {results["success"]}, 失败: {results["failed"]}'
        })
        
    except Exception as e:
        return jsonify({'error': f'导入过程中发生错误: {str(e)}'}), 500

if __name__ == '__main__':
    # 确保上传目录存在
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    app.run(debug=True, host='0.0.0.0', port=5000)
