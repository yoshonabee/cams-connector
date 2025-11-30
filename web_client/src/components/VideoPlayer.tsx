import { useState, useEffect, useRef } from 'react';
import { getVideoUrl } from '../api';
import './VideoPlayer.css';

interface VideoPlayerProps {
    deviceId: string;
    filename: string;
    onClose: () => void;
}

const CHUNK_SIZE = 2 * 1024 * 1024; // 2MB chunks

export default function VideoPlayer({ deviceId, filename, onClose }: VideoPlayerProps) {
    const [isLoading, setIsLoading] = useState(true);
    const [loadingProgress, setLoadingProgress] = useState(0);
    const [error, setError] = useState<string | null>(null);
    const [blobUrl, setBlobUrl] = useState<string | null>(null);
    const videoRef = useRef<HTMLVideoElement>(null);
    const abortControllerRef = useRef<AbortController | null>(null);

    const videoUrl = getVideoUrl(deviceId, filename);

    // Load video in chunks and create blob URL
    useEffect(() => {
        let isMounted = true;
        abortControllerRef.current = new AbortController();

        const loadVideoChunked = async () => {
            setIsLoading(true);
            setError(null);
            setLoadingProgress(0);

            try {
                // First, get the file size with a HEAD request or first chunk
                const headResponse = await fetch(videoUrl, {
                    method: 'HEAD',
                    signal: abortControllerRef.current?.signal,
                });

                if (!headResponse.ok) {
                    throw new Error(`Failed to fetch video: ${headResponse.statusText}`);
                }

                const contentLength = headResponse.headers.get('content-length');
                const totalSize = contentLength ? parseInt(contentLength, 10) : null;

                if (!totalSize) {
                    // If we can't get size, try loading first chunk to determine size
                    const firstChunkResponse = await fetch(videoUrl, {
                        headers: { Range: 'bytes=0-1023' },
                        signal: abortControllerRef.current?.signal,
                    });
                    const rangeHeader = firstChunkResponse.headers.get('content-range');
                    if (rangeHeader) {
                        const match = rangeHeader.match(/\/(\d+)$/);
                        if (match) {
                            const size = parseInt(match[1], 10);
                            // Load the entire file in chunks
                            await loadFileInChunks(size);
                            return;
                        }
                    }
                    throw new Error('Unable to determine file size');
                }

                await loadFileInChunks(totalSize);
            } catch (err) {
                if (isMounted && err instanceof Error && err.name !== 'AbortError') {
                    setError(err.message || 'Failed to load video');
                    setIsLoading(false);
                }
            }
        };

        const loadFileInChunks = async (totalSize: number) => {
            const chunks: Blob[] = [];
            let loadedBytes = 0;

            try {
                // Load file in chunks
                for (let start = 0; start < totalSize; start += CHUNK_SIZE) {
                    if (!isMounted || abortControllerRef.current?.signal.aborted) {
                        return;
                    }

                    const end = Math.min(start + CHUNK_SIZE - 1, totalSize - 1);
                    const response = await fetch(videoUrl, {
                        headers: { Range: `bytes=${start}-${end}` },
                        signal: abortControllerRef.current?.signal,
                    });

                    if (!response.ok) {
                        throw new Error(`Failed to fetch chunk: ${response.statusText}`);
                    }

                    const blob = await response.blob();
                    chunks.push(blob);
                    loadedBytes += blob.size;

                    if (isMounted) {
                        setLoadingProgress((loadedBytes / totalSize) * 100);
                    }
                }

                // Combine all chunks into a single blob
                const combinedBlob = new Blob(chunks, { type: 'video/mp4' });
                
                // Create blob URL
                const url = URL.createObjectURL(combinedBlob);
                
                if (isMounted) {
                    setBlobUrl(url);
                    setIsLoading(false);
                    setLoadingProgress(100);
                } else {
                    URL.revokeObjectURL(url);
                }
            } catch (err) {
                if (isMounted && err instanceof Error && err.name !== 'AbortError') {
                    setError(err.message || 'Failed to load video');
                    setIsLoading(false);
                }
            }
        };

        loadVideoChunked();

        return () => {
            isMounted = false;
            abortControllerRef.current?.abort();
        };
    }, [videoUrl, deviceId, filename]);

    // Cleanup blob URL on unmount
    useEffect(() => {
        return () => {
            if (blobUrl) {
                URL.revokeObjectURL(blobUrl);
            }
        };
    }, [blobUrl]);

    const handleLoadedData = () => {
        setIsLoading(false);
    };

    const handleError = () => {
        setError('Failed to play video');
        setIsLoading(false);
    };

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                onClose();
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [onClose]);

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
                            <p>載入影片中... / Loading video...</p>
                            <div className="progress-bar-container">
                                <div 
                                    className="progress-bar" 
                                    style={{ width: `${loadingProgress}%` }}
                                />
                            </div>
                            <p className="progress-text">{Math.round(loadingProgress)}%</p>
                        </div>
                    )}

                    {error && (
                        <div className="player-error">
                            <p>{error}</p>
                        </div>
                    )}

                    {blobUrl && !error && (
                        <video
                            ref={videoRef}
                            src={blobUrl}
                            controls
                            autoPlay
                            onLoadedData={handleLoadedData}
                            onError={handleError}
                            style={{ display: isLoading ? 'none' : 'block' }}
                        />
                    )}
                </div>
            </div>
        </div>
    );
}
