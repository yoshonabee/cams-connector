/**
 * API service for communicating with the Proxy Server
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export interface VideoInfo {
  filename: string;
  size: number;
  timestamp: string;
  camera: string;
}

export interface VideoListResponse {
  videos: VideoInfo[];
  total: number;
}

export interface CameraInfo {
  deviceId: string;
  cameraId: string;
}

export interface CameraListResponse {
  cameras: CameraInfo[];
  total: number;
}

/**
 * List all videos for a device/camera
 */
export async function listVideos(deviceId: string): Promise<VideoListResponse> {
  const response = await fetch(`${API_BASE}/devices/${deviceId}/videos`);

  if (!response.ok) {
    throw new Error(`Failed to list videos: ${response.statusText}`);
  }

  return response.json();
}

/**
 * List all available cameras from all connected devices
 */
export async function listCameras(): Promise<CameraListResponse> {
  const response = await fetch(`${API_BASE}/api/cameras`);

  if (!response.ok) {
    throw new Error(`Failed to list cameras: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get the URL for streaming a video
 */
export function getVideoUrl(deviceId: string, filename: string): string {
  return `${API_BASE}/devices/${deviceId}/videos/${encodeURIComponent(
    filename
  )}`;
}
