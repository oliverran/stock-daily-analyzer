import React, { useState, useEffect, useRef } from 'react';
import { Activity, Play, Terminal, TrendingUp, AlertTriangle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

function App() {
  const [analyzing, setAnalyzing] = useState(false);
  const [logs, setLogs] = useState([]);
  const [report, setReport] = useState(null);
  const [activeTab, setActiveTab] = useState('llm');
  const logEndRef = useRef(null);

  // 滚动到底部
  const scrollToBottom = () => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [logs]);

  // 获取最新报告
  const fetchReport = async () => {
    try {
      const res = await fetch('/api/latest-report');
      const data = await res.json();
      if (data && (data.status === 'success' || data.backtest)) {
        setReport(data);
      }
    } catch (e) {
      console.error("Failed to fetch report", e);
    }
  };

  // 初始化加载报告
  useEffect(() => {
    fetchReport();
  }, []);

  const startAnalysis = async () => {
    if (analyzing) return;
    setAnalyzing(true);
    setLogs([]);
    setReport(null);

    try {
      // 1. 触发后端任务
      await fetch('/api/analyze', { method: 'POST' });

      // 2. 建立 SSE 连接
      // 直接连接后端端口，绕过 Vite 代理，避免代理层的超时或断连问题
      const eventSource = new EventSource('http://localhost:8000/api/stream');

      eventSource.onopen = () => {
        console.log("SSE Connected");
      };

      eventSource.onmessage = (event) => {
        // 普通日志不做处理，因为后端使用的是自定义事件名
      };

      eventSource.addEventListener('log', (event) => {
        // 简单清理日志格式
        const msg = event.data.replace(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - (INFO|WARNING|ERROR) - /, '');
        setLogs(prev => [...prev, msg]);
      });

      eventSource.addEventListener('status', (event) => {
        if (event.data === 'finished') {
          console.log("Analysis Finished");
          eventSource.close();
          setAnalyzing(false);
          fetchReport();
        }
      });

      eventSource.onerror = (err) => {
        // 只有当状态不是 OPEN 时才认为是错误并关闭
        if (eventSource.readyState === EventSource.CLOSED) {
            console.log("SSE Closed");
            setAnalyzing(false);
            fetchReport();
        } else {
            // 在某些浏览器或网络环境下，可能会频繁触发 onerror，这里选择暂时忽略或轻量处理
            console.error("SSE Error:", err);
            // 遇到错误时尝试关闭并刷新结果，防止无限等待
            eventSource.close();
            setAnalyzing(false);
            fetchReport();
        }
      };

    } catch (e) {
      console.error(e);
      setAnalyzing(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
      {/* 顶部导航 */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="text-blue-600 h-6 w-6" />
            <h1 className="text-xl font-bold text-gray-800">Stock Daily Analyzer <span className="text-xs font-normal text-gray-500 ml-2">v1.1.0</span></h1>
          </div>
          <button
            onClick={startAnalysis}
            disabled={analyzing}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-white font-medium transition-colors ${
              analyzing ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 shadow-sm'
            }`}
          >
            {analyzing ? (
              <>
                <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                分析中...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 fill-current" />
                开始分析
              </>
            )}
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* 左侧：实时日志 (占据 5/12) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Terminal className="h-5 w-5 text-gray-600" />
              思考与分析过程
            </h2>
            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">实时日志</span>
          </div>
          <div className="bg-gray-900 rounded-xl shadow-lg overflow-hidden flex flex-col h-[600px]">
            <div className="flex-1 overflow-y-auto p-4 font-mono text-sm space-y-1 custom-scrollbar">
              {logs.length === 0 && !analyzing && (
                <div className="text-gray-500 italic text-center mt-20">点击右上角"开始分析"启动任务...</div>
              )}
              {logs.map((log, i) => (
                <div key={i} className="text-green-400 break-words leading-relaxed animate-fade-in">
                  <span className="text-gray-600 mr-2">$</span>
                  {log}
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
          </div>
        </div>

        {/* 右侧：结果展示 (占据 7/12) */}
        <div className="lg:col-span-7 space-y-6">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-gray-600" />
            分析结果看板
          </h2>

          {/* 选项卡 */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="flex border-b border-gray-200">
              <button
                onClick={() => setActiveTab('llm')}
                className={`flex-1 py-3 text-sm font-medium text-center transition-colors ${
                  activeTab === 'llm' ? 'bg-blue-50 text-blue-700 border-b-2 border-blue-600' : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                🤖 LLM智能精选
              </button>
              <button
                onClick={() => setActiveTab('today')}
                className={`flex-1 py-3 text-sm font-medium text-center transition-colors ${
                  activeTab === 'today' ? 'bg-blue-50 text-blue-700 border-b-2 border-blue-600' : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                📊 今日推荐
              </button>
              <button
                onClick={() => setActiveTab('backtest')}
                className={`flex-1 py-3 text-sm font-medium text-center transition-colors ${
                  activeTab === 'backtest' ? 'bg-blue-50 text-blue-700 border-b-2 border-blue-600' : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                ⏮ 历史回测
              </button>
            </div>

            <div className="p-6 min-h-[500px]">
              {!report ? (
                <div className="h-full flex flex-col items-center justify-center text-gray-400">
                  <Activity className="h-12 w-12 mb-4 opacity-20" />
                  <p>暂无分析结果，请先运行分析</p>
                </div>
              ) : (
                <>
                  {/* LLM 智能精选内容 */}
                  {activeTab === 'llm' && (
                    <div className="space-y-6">
                      {report.llm_picks && Object.keys(report.llm_picks).length > 0 ? (
                        Object.entries(report.llm_picks).map(([type, pick]) => (
                          <div key={type} className="bg-gradient-to-br from-indigo-50 to-blue-50 rounded-xl p-5 border border-indigo-100 shadow-sm">
                            <div className="flex justify-between items-start mb-3">
                              <span className="bg-indigo-600 text-white text-xs px-2 py-1 rounded uppercase font-bold tracking-wider">{type}</span>
                              <span className="text-2xl font-bold text-gray-900">{pick.name} <span className="text-base text-gray-500 font-normal">({pick.ticker})</span></span>
                            </div>
                            <div className="prose prose-sm text-gray-700 max-w-none bg-white/60 p-4 rounded-lg">
                              <ReactMarkdown>{pick.reason}</ReactMarkdown>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="text-center py-10 text-gray-500">LLM 未生成精选结果</div>
                      )}
                    </div>
                  )}

                  {/* 今日推荐内容 */}
                  {activeTab === 'today' && (
                    <div className="space-y-6">
                       <div className="flex justify-between text-sm text-gray-500 mb-2">
                          <span>总扫描: {report.summary?.total_scanned || 0} 只</span>
                          <span>{report.timestamp ? new Date(report.timestamp).toLocaleString() : ''}</span>
                       </div>
                       {report.summary?.recommendations && Object.entries(report.summary.recommendations).map(([type, stocks]) => (
                         <div key={type} className="space-y-2">
                           <h3 className="font-semibold text-gray-700 border-l-4 border-blue-500 pl-2">{type}</h3>
                           {stocks.length > 0 ? (
                             <div className="overflow-x-auto">
                               <table className="min-w-full divide-y divide-gray-200 text-sm">
                                 <thead className="bg-gray-50">
                                   <tr>
                                     <th className="px-3 py-2 text-left font-medium text-gray-500">股票</th>
                                     <th className="px-3 py-2 text-right font-medium text-gray-500">价格</th>
                                     <th className="px-3 py-2 text-right font-medium text-gray-500">RSI</th>
                                     <th className="px-3 py-2 text-right font-medium text-gray-500">量比</th>
                                   </tr>
                                 </thead>
                                 <tbody className="bg-white divide-y divide-gray-200">
                                   {stocks.map((s, idx) => (
                                     <tr key={idx} className="hover:bg-gray-50">
                                       <td className="px-3 py-2 font-medium text-gray-900">{s.name} <span className="text-gray-400 text-xs">({s.code})</span></td>
                                       <td className="px-3 py-2 text-right text-gray-600">¥{s.price.toFixed(2)}</td>
                                       <td className="px-3 py-2 text-right text-gray-600">{s.rsi.toFixed(0)}</td>
                                       <td className="px-3 py-2 text-right text-gray-600">{s.vol_ratio.toFixed(2)}</td>
                                     </tr>
                                   ))}
                                 </tbody>
                               </table>
                             </div>
                           ) : (
                             <p className="text-sm text-gray-400 pl-4 py-2 italic">无符合标的</p>
                           )}
                         </div>
                       ))}
                    </div>
                  )}

                  {/* 历史回测内容 */}
                  {activeTab === 'backtest' && (
                    <div>
                      {report.backtest ? (
                        <div className="space-y-6">
                           <div className="grid grid-cols-2 gap-4">
                             <div className="bg-green-50 p-4 rounded-lg border border-green-100 text-center">
                               <div className="text-sm text-green-600 mb-1">准确率</div>
                               <div className="text-3xl font-bold text-green-700">{(report.backtest.accuracy_rate * 100).toFixed(0)}%</div>
                             </div>
                             <div className="bg-blue-50 p-4 rounded-lg border border-blue-100 text-center">
                               <div className="text-sm text-blue-600 mb-1">平均收益</div>
                               <div className="text-3xl font-bold text-blue-700">{(report.backtest.avg_return * 100).toFixed(2)}%</div>
                             </div>
                           </div>
                           
                           <div className="bg-white rounded-lg border border-gray-200 p-4 text-sm space-y-2">
                              <div className="flex justify-between">
                                <span className="text-gray-500">验证周期:</span>
                                <span className="font-medium">3天前推荐</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-500">样本总数:</span>
                                <span className="font-medium">{report.backtest.total_recommendations} 只</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-500">胜/平/负:</span>
                                <span className="font-medium text-green-600">{report.backtest.correct_count}</span> / 
                                <span className="font-medium text-gray-600">{report.backtest.neutral_count}</span> / 
                                <span className="font-medium text-red-600">{report.backtest.wrong_count}</span>
                              </div>
                           </div>

                           {report.backtest.best_pick && (
                             <div className="flex items-center gap-3 p-3 bg-yellow-50 rounded-lg text-sm text-yellow-800">
                               <TrendingUp className="h-4 w-4" />
                               <span>最佳表现: <strong>{report.backtest.best_pick}</strong> ({(report.backtest.best_return * 100).toFixed(2)}%)</span>
                             </div>
                           )}
                        </div>
                      ) : (
                        <div className="text-center py-10 text-gray-400">
                           <AlertTriangle className="h-10 w-10 mx-auto mb-2 opacity-20" />
                           暂无回测数据
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
