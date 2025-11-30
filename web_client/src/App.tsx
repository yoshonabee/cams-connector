import { useState, useEffect } from "react";
import { listVideos, listCameras } from "./api";
import type { VideoInfo, CameraInfo } from "./api";
import VideoCard from "./components/VideoCard";
import VideoPlayer from "./components/VideoPlayer";
import "./App.css";

function App() {
  const [cameras, setCameras] = useState<CameraInfo[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState<string>("");
  const [videos, setVideos] = useState<VideoInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingCameras, setLoadingCameras] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedVideo, setSelectedVideo] = useState<VideoInfo | null>(null);

  // Load cameras on component mount
  useEffect(() => {
    loadCameras();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch videos when selectedCameraId changes
  useEffect(() => {
    if (selectedCameraId) {
      loadVideos();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCameraId]);

  const loadCameras = async () => {
    setLoadingCameras(true);
    setError(null);

    try {
      const response = await listCameras();
      setCameras(response.cameras);
      // Set first camera as default if available
      if (response.cameras.length > 0 && !selectedCameraId) {
        setSelectedCameraId(response.cameras[0].cameraId);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load cameras");
    } finally {
      setLoadingCameras(false);
    }
  };

  const loadVideos = async () => {
    if (!selectedCameraId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await listVideos(selectedCameraId);
      setVideos(response.videos);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load videos");
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
          </div>
        </div>
      </header>

      <main className="main container">
        <div className="controls">
          <div className="control-group">
            <label htmlFor="device-select">選擇監視器 / Camera:</label>
            <select
              id="device-select"
              value={selectedCameraId}
              onChange={(e) => setSelectedCameraId(e.target.value)}
              className="device-select"
              disabled={loadingCameras || cameras.length === 0}
            >
              {cameras.length === 0 ? (
                <option value="">載入中...</option>
              ) : (
                cameras.map((camera) => (
                  <option
                    key={`${camera.deviceId}-${camera.cameraId}`}
                    value={camera.cameraId}
                  >
                    {camera.cameraId} ({camera.deviceId})
                  </option>
                ))
              )}
            </select>
          </div>

          <button
            onClick={loadVideos}
            className="btn"
            disabled={loading || !selectedCameraId}
          >
            {loading ? <span className="spinner"></span> : "🔄"}
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
          deviceId={selectedCameraId}
          filename={selectedVideo.filename}
          onClose={handleClosePlayer}
        />
      )}
    </div>
  );
}

export default App;
