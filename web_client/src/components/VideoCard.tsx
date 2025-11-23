import type { VideoInfo } from '../api';
import './VideoCard.css';

interface VideoCardProps {
    video: VideoInfo;
    onClick: () => void;
}

export default function VideoCard({ video, onClick }: VideoCardProps) {
    // Format timestamp for display
    const formatTimestamp = (isoString: string) => {
        const date = new Date(isoString);
        return new Intl.DateTimeFormat('zh-TW', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        }).format(date);
    };

    // Format file size
    const formatSize = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    return (
        <div className="video-card" onClick={onClick}>
            <div className="video-thumbnail">
                <div className="play-icon">▶</div>
            </div>

            <div className="video-info">
                <h4 className="video-filename">{video.filename}</h4>
                <p className="video-meta text-secondary">
                    {formatTimestamp(video.timestamp)}
                </p>
                <p className="video-size text-muted">
                    {formatSize(video.size)}
                </p>
            </div>
        </div>
    );
}
