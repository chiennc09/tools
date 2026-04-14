import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Play, Square, Activity, Settings, Smartphone } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

interface DeviceStatus {
  is_running: boolean;
  mode: string[];
  resolution: string;
}

export default function App() {
  const [devices, setDevices] = useState<string[]>([]);
  const [status, setStatus] = useState<Record<string, DeviceStatus>>({});
  const [logs, setLogs] = useState<Record<string, string[]>>({});
  
  // Config state
  const [modes, setModes] = useState<Record<string, string[]>>({});
  const [resolutions, setResolutions] = useState<Record<string, string>>({});
  const [minSleeps, setMinSleeps] = useState<Record<string, number>>({});
  const [maxSleeps, setMaxSleeps] = useState<Record<string, number>>({});
  const [globalBaseRes, setGlobalBaseRes] = useState<string>('720x1280');
  
  const logsEndRef = useRef<Record<string, HTMLDivElement | null>>({});

  useEffect(() => {
    Object.keys(logs).forEach(dev => {
      if (logsEndRef.current[dev]) {
        logsEndRef.current[dev]?.scrollIntoView({ behavior: 'smooth' });
      }
    });
  }, [logs]);

  useEffect(() => {
    fetchGlobalConfig();
    fetchDevices();
    fetchStatus();

    let ws: WebSocket;
    let reconnectTimeout: NodeJS.Timeout;

    const connectWs = () => {
      ws = new WebSocket('ws://localhost:8000/ws/logs');
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.device_id && data.message) {
          setLogs((prev) => {
            const deviceLogs = prev[data.device_id] || [];
            return {
              ...prev,
              [data.device_id]: [...deviceLogs, `[${new Date().toLocaleTimeString()}] ${data.message}`].slice(-50)
            };
          });
        }
      };
      ws.onclose = () => {
        // Tự động kết nối lại Web Socket nếu bị đứt (ví dụ Uvicorn restart)
        reconnectTimeout = setTimeout(connectWs, 2000);
      };
    };

    connectWs();

    const interval = setInterval(() => {
      fetchDevices();
      fetchStatus();
    }, 5000);

    return () => {
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
      clearTimeout(reconnectTimeout);
      clearInterval(interval);
    };
  }, []);

  const fetchGlobalConfig = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/config`);
      if (res.data && res.data.data) {
        setGlobalBaseRes(res.data.data.base_resolution || '720x1280');
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleGlobalResChange = async (newRes: string) => {
    try {
      setGlobalBaseRes(newRes);
      await axios.post(`${API_BASE}/api/config`, { base_resolution: newRes });
    } catch (e) {
      alert("Lỗi khi lưu cấu hình chung");
    }
  };

  const fetchDevices = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/devices`);
      if (res.data.status === 'success') {
        setDevices(res.data.devices);
        setModes(prev => {
          const newModes = { ...prev };
          res.data.devices.forEach((dev: string) => {
            if (!newModes[dev]) newModes[dev] = ['NEWFEED'];
          });
          return newModes;
        });
        setResolutions(prev => {
          const newRes = { ...prev };
          res.data.devices.forEach((dev: string) => {
            if (!newRes[dev]) newRes[dev] = '720x1280';
          });
          return newRes;
        });
        setMinSleeps(prev => {
          const newMin = { ...prev };
          res.data.devices.forEach((dev: string) => {
            if (!newMin[dev]) newMin[dev] = 10; // Mặc định min 10s
          });
          return newMin;
        });
        setMaxSleeps(prev => {
          const newMax = { ...prev };
          res.data.devices.forEach((dev: string) => {
            if (!newMax[dev]) newMax[dev] = 25; // Mặc định max 25s
          });
          return newMax;
        });
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchStatus = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/bot/status`);
      if (res.data.status === 'success') {
        setStatus(res.data.data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleStart = async (deviceId: string) => {
    try {
      await axios.post(`${API_BASE}/api/bot/${deviceId}/start`, {
        mode: modes[deviceId] || ['NEWFEED'],
        resolution: resolutions[deviceId] || '720x1280',
        min_sleep: Number(minSleeps[deviceId]) || 10.0,
        max_sleep: Number(maxSleeps[deviceId]) || 25.0
      });
      fetchStatus();
      setLogs((prev) => ({...prev, [deviceId]: ['--- Bắt đầu phiên làm việc mới ---']}));
    } catch (e: any) {
      alert("Lỗi khi bắt đầu: " + (e.response?.data?.detail || e.message));
    }
  };

  const handleStop = async (deviceId: string) => {
    try {
      await axios.post(`${API_BASE}/api/bot/${deviceId}/stop`);
      fetchStatus();
    } catch (e: any) {
      alert("Lỗi khi dừng: " + (e.response?.data?.detail || e.message));
    }
  };

  const handleModeChange = (device: string, option: string, checked: boolean) => {
    setModes(prev => {
      const currentModes = prev[device] || [];
      let newModes;
      if (checked) {
        newModes = [...currentModes, option];
      } else {
        newModes = currentModes.filter(m => m !== option);
        if (newModes.length === 0) newModes = ['NEWFEED']; // prevent empty
      }
      return { ...prev, [device]: newModes };
    });
  };

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold text-slate-800 flex items-center gap-2">
              <Activity className="text-blue-600" />
              ToolFace Automation Central
            </h1>
            <p className="text-slate-500 mt-2">Hệ thống quản lý Farm thiết bị đa luồng - Hiện tại: {devices.length} thiết bị đang kết nối</p>
          </div>
          
          <div className="bg-white p-3 rounded-lg shadow-sm border border-slate-200 flex items-center gap-3">
            <Settings className="text-slate-400" size={20} />
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase">Độ phân giải gốc thư mục /img</label>
              <select 
                className="mt-1 w-full border-b border-slate-200 text-sm focus:outline-none focus:border-blue-500 bg-transparent font-medium"
                value={globalBaseRes}
                onChange={(e) => handleGlobalResChange(e.target.value)}
              >
                <option value="720x1280">720 x 1280 (Mặc định)</option>
                <option value="1080x1920">1080 x 1920</option>
                <option value="540x960">540 x 960</option>
              </select>
            </div>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {devices.map((device) => {
            const isRunning = status[device]?.is_running || false;
            const currentModes = isRunning ? (status[device]?.mode || ['NEWFEED']) : (modes[device] || ['NEWFEED']);
            const currentRes = status[device]?.resolution || resolutions[device];
            const deviceLogs = logs[device] || [];

            return (
              <div key={device} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${isRunning ? 'bg-green-500 animate-pulse' : 'bg-slate-300'}`}></div>
                    <h3 className="font-semibold text-slate-700 flex items-center gap-2">
                      <Smartphone size={18}/>
                      {device}
                    </h3>
                  </div>
                  <div>
                    {isRunning ? (
                      <button onClick={() => handleStop(device)} className="flex items-center gap-1 bg-red-100 text-red-700 px-4 py-2 rounded-lg font-medium hover:bg-red-200 transition-colors">
                        <Square size={16} /> Dừng
                      </button>
                    ) : (
                      <button onClick={() => handleStart(device)} className="flex items-center gap-1 bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors">
                        <Play size={16} /> Bắt đầu chạy
                      </button>
                    )}
                  </div>
                </div>

                <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4 border-b border-slate-100">
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Tổ Hợp Kịch Bản Hoạt Động</label>
                    <div className="flex flex-col gap-2 bg-slate-50 rounded-lg p-3 text-sm">
                      <label className="flex items-center gap-3 cursor-pointer">
                        <input type="checkbox" disabled={isRunning} 
                           checked={currentModes.includes('NEWFEED')}
                           onChange={(e) => handleModeChange(device, 'NEWFEED', e.target.checked)}
                           className="w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500 disabled:opacity-50" />
                        <span className="text-slate-700 font-medium">Lướt Newsfeed & Like</span>
                      </label>
                      <label className="flex items-center gap-3 cursor-pointer">
                        <input type="checkbox" disabled={isRunning} 
                           checked={currentModes.includes('REELS')}
                           onChange={(e) => handleModeChange(device, 'REELS', e.target.checked)}
                           className="w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500 disabled:opacity-50" />
                        <span className="text-slate-700 font-medium">Lướt xem Reels</span>
                      </label>
                      <label className="flex items-center gap-3 cursor-pointer">
                        <input type="checkbox" disabled={isRunning} 
                           checked={currentModes.includes('COMMENT')}
                           onChange={(e) => handleModeChange(device, 'COMMENT', e.target.checked)}
                           className="w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500 disabled:opacity-50" />
                        <span className="text-slate-700 font-medium">Comment</span>
                      </label>
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Độ Phân Giải Giả Lập</label>
                    <select 
                      disabled={isRunning}
                      className="w-full border border-slate-300 rounded-md p-2.5 text-sm disabled:bg-slate-100 bg-white"
                      value={resolutions[device] || '720x1280'}
                      onChange={(e) => setResolutions({...resolutions, [device]: e.target.value})}
                    >
                      <option value="720x1280">720 x 1280 (Mặc định)</option>
                      <option value="1080x1920">1080 x 1920</option>
                      <option value="540x960">540 x 960</option>
                    </select>
                  </div>
                </div>

                <div className="p-4 grid grid-cols-2 gap-4 border-b border-slate-100 bg-slate-50">
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Thời gian đọc ngẫu nhiên Nhỏ nhất (Giây)</label>
                    <input 
                      type="number"
                      disabled={isRunning}
                      className="w-full border border-slate-300 rounded-md p-2 text-sm disabled:bg-slate-100"
                      value={minSleeps[device] || ''}
                      onChange={(e) => setMinSleeps({...minSleeps, [device]: Number(e.target.value)})}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Thời gian đọc ngẫu nhiên Lớn nhất (Giây)</label>
                    <input 
                      type="number"
                      disabled={isRunning}
                      className="w-full border border-slate-300 rounded-md p-2 text-sm disabled:bg-slate-100"
                      value={maxSleeps[device] || ''}
                      onChange={(e) => setMaxSleeps({...maxSleeps, [device]: Number(e.target.value)})}
                    />
                  </div>
                </div>

                {/* Log terminal */}
                <div className="bg-slate-900 p-4 h-64 overflow-y-auto">
                  <div className="font-mono text-xs text-green-400 space-y-1">
                    {deviceLogs.length === 0 && <div className="text-slate-600">Đang chờ sự kiện...</div>}
                    {deviceLogs.map((log, i) => (
                      <div key={i}>{log}</div>
                    ))}
                    <div ref={(el) => logsEndRef.current[device] = el} />
                  </div>
                </div>
              </div>
            );
          })}

          {devices.length === 0 && (
            <div className="col-span-full py-12 text-center text-slate-500 bg-white rounded-xl shadow-sm border border-slate-200">
              <Smartphone className="mx-auto h-12 w-12 text-slate-300 mb-3" />
              <p>Không tìm thấy thiết bị ADB nào kết nối.</p>
              <p className="text-sm">Hãy cắm cáp USB hoặc mở Emulator và chạy lệnh <code>adb devices</code>.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
