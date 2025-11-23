import { useState, useEffect } from 'react';
import { listVideos, checkHealth } from './api';
import type { VideoInfo } from './api';
import VideoCard from './components/VideoCard';
import VideoPlayer from './components/VideoPlayer';
import './App.css';

function App() {
  const [deviceId, setDeviceId] = useState('cam1');
  const [videos, setVideos] = useState<VideoInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedVideo, setSelectedVideo] = useState<VideoInfo | null>(null);
  const [healthStatus, setHealthStatus] = useState<{ status: string; connected_devices: number } | null>(null);

  // Fetch health status on mount
  useEffect(() => {
    checkHealth()
      .then(setHealthStatus)
      .catch(() => setHealthStatus(null));
  }, []);

  // Fetch videos when deviceId changes
  useEffect(() => {
    loadVideos();
  }, [deviceId]);

  const loadVideos = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await listVideos(deviceId);
      setVideos(response.videos);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load videos');
    } finally {
      setLoading(false);
    }
  };

  const handleVideoClick = (video: VideoInfo) => {
    setSelectedVideo(video);
  };

  const handleClosePlayer = () => {
    setSelectedVideo(null);
  };

  return (
    <div className="app">
      <header className="header">
        <div className="container">
          <div className="header-content">
            <div>
              <h1>📹 監視器影片瀏覽系統</h1>
              <p className="text-secondary">Camera Video Browsing System</p>
            </div>

            {healthStatus && (
              <div className="health-status">
                <span className={`status-indicator ${healthStatus.status === 'ok' ? 'status-ok' : 'status-error'}`}>
                  {healthStatus.status === 'ok' ? '🟢' : '🔴'}
                </span>
                <span className="text-secondary">
                  {healthStatus.connected_devices} device(s) connected
                </span>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="main container">
        <div className="controls">
          <div className="control-group">
            <label htmlFor="device-select">選擇監視器 / Camera:</label>
            <select
              id="device-select"
              value={deviceId}
              onChange={(e) => setDeviceId(e.target.value)}
              className="device-select"
            >
              <option value="cam1">Camera 1</option>
              <option value="cam2">Camera 2</option>
            </select>
          </div>

          <button onClick={loadVideos} className="btn" disabled={loading}>
            {loading ? <span className="spinner"></span> : '🔄'}
            重新整理 / Refresh
          </button>
        </div>

        {error && (
          <div className="error-message">
            <p>❌ {error}</p>
          </div>
        )}

        {loading ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <p className="text-secondary">載入中...</p>
          </div>
        ) : videos.length === 0 ? (
          <div className="empty-state">
            <p className="text-muted">📂 沒有找到影片 / No videos found</p>
          </div>
        ) : (
          <div className="videos-grid grid-3">
            {videos.map((video) => (
              <VideoCard
                key={video.filename}
                video={video}
                onClick={() => handleVideoClick(video)}
              />
            ))}
          </div>
        )}
      </main>

      {selectedVideo && (
        <VideoPlayer
          deviceId={deviceId}
          filename={selectedVideo.filename}
          onClose={handleClosePlayer}
        />
      )}
    </div>
  );
}

export default App;
