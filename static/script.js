let currentFilename = '';

function showTab(tabName) {
    // 隐藏所有标签页
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // 显示选中的标签页
    document.getElementById(tabName + '-tab').classList.add('active');
    event.target.classList.add('active');
}

function uploadFile() {
    const fileInput = document.getElementById('csv_file');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('请选择CSV文件');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    document.getElementById('uploadBtn').disabled = true;
    document.getElementById('uploadBtn').textContent = '上传中...';
    
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('错误: ' + data.error);
            resetUploadButton();
            return;
        }
        
        currentFilename = data.filename;
        showPreview(data.preview, data.columns, data.total_rows);
        resetUploadButton();
    })
    .catch(error => {
        alert('上传失败: ' + error);
        resetUploadButton();
    });
}

function resetUploadButton() {
    document.getElementById('uploadBtn').disabled = false;
    document.getElementById('uploadBtn').textContent = '重新上传';
}

function showPreview(data, columns, totalRows) {
    let tableHtml = `<table><tr>`;
    
    columns.forEach(col => {
        tableHtml += `<th>${col}</th>`;
    });
    tableHtml += `</tr>`;
    
    data.forEach(row => {
        tableHtml += `<tr>`;
        columns.forEach(col => {
            const value = row[col];
            tableHtml += `<td title="${value}">${value || ''}</td>`;
        });
        tableHtml += `</tr>`;
    });
    
    tableHtml += `</table>`;
    
    document.getElementById('previewTable').innerHTML = tableHtml;
    document.getElementById('totalRows').textContent = totalRows;
    document.getElementById('previewSection').style.display = 'block';
}

function startImport() {
    const kumaUrl = document.getElementById('kuma_url').value;
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    if (!kumaUrl || !username || !password) {
        alert('请填写Uptime Kuma地址、用户名和密码');
        return;
    }
    
    document.getElementById('previewSection').style.display = 'none';
    document.getElementById('progress').style.display = 'block';
    document.getElementById('importBtn').disabled = true;
    
    fetch('/import', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            filename: currentFilename,
            kuma_url: kumaUrl,
            username: username,
            password: password
        })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('progress').style.display = 'none';
        
        if (data.error) {
            showResults('error', '导入失败: ' + data.error);
            return;
        }
        
        const results = data.results;
        let message = `导入完成！成功: ${results.success}, 失败: ${results.failed}`;
        
        if (results.errors.length > 0) {
            message += '<div class="error-list"><strong>错误详情:</strong><ul>';
            results.errors.forEach(error => {
                message += `<li>${error}</li>`;
            });
            message += '</ul></div>';
        }
        
        showResults('success', message);
    })
    .catch(error => {
        document.getElementById('progress').style.display = 'none';
        showResults('error', '导入过程中发生错误: ' + error);
    })
    .finally(() => {
        document.getElementById('importBtn').disabled = false;
    });
}

function loadMonitors() {
    const kumaUrl = document.getElementById('delete_kuma_url').value;
    const username = document.getElementById('delete_username').value;
    const password = document.getElementById('delete_password').value;
    
    if (!kumaUrl || !username || !password) {
        alert('请填写Uptime Kuma地址、用户名和密码');
        return;
    }
    
    document.getElementById('loadBtn').disabled = true;
    document.getElementById('loadBtn').textContent = '加载中...';
    
    fetch('/get-monitors', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            kuma_url: kumaUrl,
            username: username,
            password: password
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('错误: ' + data.error);
            resetLoadButton();
            return;
        }
        
        displayMonitorsList(data.monitors);
        resetLoadButton();
    })
    .catch(error => {
        alert('加载失败: ' + error);
        resetLoadButton();
    });
}

function resetLoadButton() {
    document.getElementById('loadBtn').disabled = false;
    document.getElementById('loadBtn').textContent = '加载监控项';
}

function displayMonitorsList(monitors) {
    let tableHtml = `<table>
        <tr>
            <th><input type="checkbox" id="selectAll" onchange="toggleSelectAll(this.checked)"></th>
            <th>ID</th>
            <th>名称</th>
            <th>类型</th>
            <th>URL</th>
            <th>状态</th>
        </tr>`;
    
    monitors.forEach(monitor => {
        const monitorId = monitor.id_str || monitor.id.toString();
        tableHtml += `
        <tr>
            <td><input type="checkbox" class="monitor-checkbox" value="${monitorId}" data-id="${monitor.id}"></td>
            <td>${monitor.id}</td>
            <td>${monitor.name}</td>
            <td>${monitor.type}</td>
            <td>${monitor.url}</td>
            <td>${monitor.active ? '✅' : '❌'}</td>
        </tr>`;
    });
    
    tableHtml += `</table>`;
    
    document.getElementById('monitorsTable').innerHTML = tableHtml;
    document.getElementById('monitorsCount').textContent = `(${monitors.length})`;
    document.getElementById('monitorsList').style.display = 'block';
}

function toggleSelectAll(checked) {
    document.querySelectorAll('.monitor-checkbox').forEach(checkbox => {
        checkbox.checked = checked;
    });
}

function selectAll() {
    document.querySelectorAll('.monitor-checkbox').forEach(checkbox => {
        checkbox.checked = true;
    });
    document.getElementById('selectAll').checked = true;
}

function selectNone() {
    document.querySelectorAll('.monitor-checkbox').forEach(checkbox => {
        checkbox.checked = false;
    });
    document.getElementById('selectAll').checked = false;
}

function selectInvert() {
    document.querySelectorAll('.monitor-checkbox').forEach(checkbox => {
        checkbox.checked = !checkbox.checked;
    });
}

function getSelectedMonitorIds() {
    const selectedIds = [];
    document.querySelectorAll('.monitor-checkbox:checked').forEach(checkbox => {
        const monitorId = checkbox.getAttribute('data-id') || checkbox.value;
        selectedIds.push(parseInt(monitorId));
    });
    return selectedIds;
}

function deleteSelected() {
    const selectedIds = getSelectedMonitorIds();
    if (selectedIds.length === 0) {
    alert('请选择要删除的监控项');
    return;
    }

    let deleteInfo = "确定要删除以下监控项吗？\n\n";
    document.querySelectorAll('.monitor-checkbox:checked').forEach(checkbox => {
        const row = checkbox.closest('tr');
        const name = row.cells[2].textContent;
        const type = row.cells[3].textContent;
        deleteInfo += `• ${name} (${type})\n`;
    });
    deleteInfo += `\n总共 ${selectedIds.length} 个监控项，此操作不可撤销！`;

    if (!confirm(deleteInfo)) {
        return;
    }

    const kumaUrl = document.getElementById('delete_kuma_url').value;
    const username = document.getElementById('delete_username').value;
    const password = document.getElementById('delete_password').value;

    document.getElementById('deleteSelectedBtn').disabled = true;
    document.getElementById('progress').style.display = 'block';

    fetch('/delete-monitors', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            kuma_url: kumaUrl,
            username: username,
            password: password,
            monitor_ids: selectedIds
        })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('progress').style.display = 'none';

        if (data.error) {
            showResults('error', '删除失败: ' + data.error);
            return;
        }

        const results = data.results;
        let message = `删除完成！成功: ${results.success}, 失败: ${results.failed}`;

        if (results.errors.length > 0) {
            message += '<div class="error-list"><strong>错误详情:</strong><ul>';
            results.errors.forEach(error => {
                message += `<li>${error}</li>`;
            });
            message += '</ul></div>';
        }

        showResults('success', message);

        // 重新加载监控项列表
        if (results.success > 0) {
            setTimeout(loadMonitors, 1000);
        }
    })
    .catch(error => {
        document.getElementById('progress').style.display = 'none';
        showResults('error', '删除过程中发生错误: ' + error);
    })
    .finally(() => {
        document.getElementById('deleteSelectedBtn').disabled = false;
    });
}

function deleteByFilter() {
    const kumaUrl = document.getElementById('filter_kuma_url').value;
    const username = document.getElementById('filter_username').value;
    const password = document.getElementById('filter_password').value;

    if (!kumaUrl || !username || !password) {
        alert('请填写Uptime Kuma地址、用户名和密码');
        return;
    }

    const filters = {
        name_filter: document.getElementById('name_filter').value,
        name_keyword: document.getElementById('name_keyword').value,
        type_filter: document.getElementById('type_filter').value
    };

    if (!confirm('确定要根据条件删除监控项吗？此操作不可撤销！')) {
        return;
    }

    document.getElementById('filterDeleteBtn').disabled = true;
    document.getElementById('progress').style.display = 'block';

    fetch('/delete-by-filter', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            kuma_url: kumaUrl,
            username: username,
            password: password,
            filters: filters
        })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('progress').style.display = 'none';

        if (data.error) {
            showResults('error', '删除失败: ' + data.error);
            return;
        }

        const results = data.results;
        let message = `找到 ${results.matched_count} 个匹配项，删除完成！成功: ${results.success}, 失败: ${results.failed}`;

        if (results.errors.length > 0) {
            message += '<div class="error-list"><strong>错误详情:</strong><ul>';
            results.errors.forEach(error => {
                message += `<li>${error}</li>`;
            });
            message += '</ul></div>';
        }

        showResults('success', message);
    })
    .catch(error => {
        document.getElementById('progress').style.display = 'none';
        showResults('error', '删除过程中发生错误: ' + error);
    })
    .finally(() => {
        document.getElementById('filterDeleteBtn').disabled = false;
    });
}

function showResults(type, message) {
    const resultsDiv = document.getElementById('results');
    resultsDiv.className = 'results ' + type;
    resultsDiv.innerHTML = `<h3>${type === 'success' ? '✅ 操作成功' : '❌ 操作失败'}</h3><div>${message}</div>`;
    resultsDiv.style.display = 'block';

    // 5秒后自动隐藏结果
    setTimeout(() => {
        resultsDiv.style.display = 'none';
    }, 5000);
}
