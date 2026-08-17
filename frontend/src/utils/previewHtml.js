// 前端在线预览的 DOCX / XLSX 自包含 HTML（供 iframe srcdoc 使用）。
// 放在 .js 文件而非 .vue 的 <script> 里，是为了避免 Vue SFC 解析器被
// 字符串中的 </script> / </style> 干扰而错误切分块。

export function docxPreviewHtml(url) {
  return `<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/mammoth@1.8.0/mammoth.browser.min.js"
    onerror="document.getElementById('container').innerHTML='<div class=error>mammoth.js CDN 加载失败，请检查网络连接</div>'">
</script>
<style>
body { font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; margin: 0; padding: 24px; }
.loading { text-align: center; padding: 40px; color: #999; }
.error { color: #c0392b; padding: 40px; text-align: center; }
</style></head><body>
<div id="container" class="loading">正在加载文档预览...</div>
<script>
(function() {
    var container = document.getElementById('container');
    if (typeof mammoth !== 'undefined') {
        doPreview();
    } else {
        var n = 0, t = setInterval(function() {
            if (typeof mammoth !== 'undefined') { clearInterval(t); doPreview(); }
            if (++n > 50) { clearInterval(t); container.innerHTML = '<div class=error>mammoth.js 加载超时（5秒），请刷新重试</div>'; }
        }, 100);
    }
    function doPreview() {
        fetch('${url}')
            .then(function(r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.arrayBuffer(); })
            .then(function(buf) {
                return mammoth.convertToHtml({arrayBuffer: buf},
                    { styleMap: [
                        "p[style-name='Normal'] => p:fresh",
                        "r[style-name='Strong'] => strong:fresh"
                    ]});
            })
            .then(function(result) {
                container.innerHTML = result.value;
                container.className = '';
            })
            .catch(function(e) {
                container.innerHTML = '<div class=error>预览失败: ' + e.message + '<br><small>请下载后用本机 Word 查看</small></div>';
            });
    }
})();
</script>
</body></html>`
}

export function xlsxPreviewHtml(url) {
  return `<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="https://cdn.sheetjs.com/xlsx-0.20.2/package/dist/xlsx.full.min.js"
    onerror="document.getElementById('container').innerHTML='<div class=error>SheetJS CDN 加载失败，请检查网络连接</div>'">
</script>
<style>
body { font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; margin: 0; display: flex; flex-direction: column; height: 100vh; }
#tabs { display: flex; gap: 4px; padding: 8px; background: #f5f5f5; border-bottom: 1px solid #ddd; flex-wrap: wrap; }
#tabs button { padding: 6px 16px; border: 1px solid #ccc; border-radius: 4px 4px 0 0; cursor: pointer; font-size: 14px; font-weight: bold; }
#container { flex: 1; overflow: auto; padding: 16px; }
#container table { width: 100%; border-collapse: collapse; font-size: 14px; }
#container th, #container td { border: 1px solid #ddd; padding: 6px 12px; text-align: left; white-space: nowrap; }
#container td { overflow: hidden; text-overflow: ellipsis; }
.loading { text-align: center; padding: 40px; color: #999; }
.error { color: #c0392b; padding: 40px; text-align: center; }
</style></head><body>
<div id="tabs"></div>
<div id="container" class="loading">正在加载表格预览...</div>
<script>
(function() {
    var container = document.getElementById('container');
    var tabsContainer = document.getElementById('tabs');
    if (typeof XLSX !== 'undefined') {
        doPreview();
    } else {
        var n = 0, t = setInterval(function() {
            if (typeof XLSX !== 'undefined') { clearInterval(t); doPreview(); }
            if (++n > 50) { clearInterval(t); container.innerHTML = '<div class=error>SheetJS 加载超时（5秒），请刷新重试</div>'; }
        }, 100);
    }
    function doPreview() {
        fetch('${url}')
            .then(function(r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.arrayBuffer(); })
            .then(function(buf) {
                var wb = XLSX.read(new Uint8Array(buf), {type: 'array'});
                var names = wb.SheetNames;
                var allSheets = {};
                names.forEach(function(name) {
                    allSheets[name] = XLSX.utils.sheet_to_html(wb.Sheets[name]);
                });
                tabsContainer.innerHTML = '';
                names.forEach(function(name, idx) {
                    var btn = document.createElement('button');
                    btn.textContent = name;
                    var isActive = idx === 0;
                    btn.style.background = isActive ? '#1976d2' : '#fff';
                    btn.style.color = isActive ? '#fff' : '#333';
                    btn.style.borderBottom = isActive ? '1px solid #1976d2' : '1px solid #ccc';
                    btn.onclick = function() {
                        var buttons = tabsContainer.querySelectorAll('button');
                        buttons.forEach(function(b) { b.style.background='#fff'; b.style.color='#333'; b.style.borderBottom='1px solid #ccc'; });
                        btn.style.background = '#1976d2';
                        btn.style.color = '#fff';
                        btn.style.borderBottom = '1px solid #1976d2';
                        container.innerHTML = allSheets[name];
                    };
                    tabsContainer.appendChild(btn);
                });
                if (names.length > 0) {
                    container.innerHTML = allSheets[names[0]];
                } else {
                    container.innerHTML = '<div class=loading>无工作表</div>';
                }
            })
            .catch(function(e) {
                container.innerHTML = '<div class=error>预览失败: ' + e.message + '<br><small>请下载后用本机 Excel 查看</small></div>';
            });
    }
})();
</script>
</body></html>`
}
