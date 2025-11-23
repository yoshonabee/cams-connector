import { useState, useEffect, useRef } from 'react';
import { getVideoUrl } from '../api';
import './VideoPlayer.css';

interface VideoPlayerProps {
    deviceId: string;
    filename: string;
    onClose: () => void;
}

export default function VideoPlayer({ deviceId, filename, onClose }: VideoPlayerProps) {
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const videoRef = useRef<HTMLVideoElement>(null);

    const videoUrl = getVideoUrl(deviceId, filename);

    useEffect(() => {
        // Reset state when video changes
        setIsLoading(true);
        setError(null);
    }, [videoUrl]);

    const handleLoadedData = () => {
        setIsLoading(false);
    };

    const handleError = () => {
        setError('Failed to load video');
        setIsLoading(false);
    };

    const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
            onClose();
        }
    };

    useEffect(() => {
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);

    return (
        <div className="player-overlay" onClick={onClose}>
            <div className="player-container" onClick={(e) => e.stopPropagation()}>
                <div className="player-header">
                    <h3>{filename}</h3>
                    <button className="btn-close" onClick={onClose} aria-label="Close">
                        ✕
                    </button>
                </div>

                <div className="player-content">
                    {isLoading && (
                        <div className="player-loading">
                            <div className="spinner"></div>
                            <p>Loading video...</p>
                        </div>
                    )}

                    {error && (
                        <div className="player-error">
                            <p>{error}</p>
                        </div>
                    )}

                    <video
                        ref={videoRef}
                        src={videoUrl}
                        controls
                        autoPlay
                        onLoadedData={handleLoadedData}
                        onError={handleError}
                        style={{ display: isLoading || error ? 'none' : 'block' }}
                    />
                </div>
            </div>
        </div>
    );
}
