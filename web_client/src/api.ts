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
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CameraInfo {
  deviceId: string;
  cameraId: string;
}

// Backend response format (snake_case)
interface CameraInfoResponse {
  device_id: string;
  camera_id: string;
}

interface CameraListResponseRaw {
  cameras: CameraInfoResponse[];
  total: number;
}

export interface CameraListResponse {
  cameras: CameraInfo[];
  total: number;
}

/**
 * List all videos for a device/camera with filtering and pagination
 */
export async function listVideos(
  deviceId: string,
  options?: {
    date?: string; // YYYYmmdd format
    hour?: number; // 0-23
    page?: number;
    page_size?: number;
  }
): Promise<VideoListResponse> {
  const params = new URLSearchParams();
  
  if (options?.date) {
    params.append('date', options.date);
  }
  if (options?.hour !== undefined) {
    params.append('hour', options.hour.toString());
  }
  if (options?.page !== undefined) {
    params.append('page', options.page.toString());
  }
  if (options?.page_size !== undefined) {
    params.append('page_size', options.page_size.toString());
  }

  const queryString = params.toString();
  const url = `${API_BASE}/devices/${deviceId}/videos${queryString ? `?${queryString}` : ''}`;
  
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to list videos: ${response.statusText}`);
  }

  return response.json();
}

/**
 * List all available cameras from all connected devices
 */
export async function listCameras(): Promise<CameraListResponse> {
  const response = await fetch(`${API_BASE}/cameras`);

  if (!response.ok) {
    throw new Error(`Failed to list cameras: ${response.statusText}`);
  }

  const data: CameraListResponseRaw = await response.json();

  // Convert snake_case to camelCase
  return {
    cameras: data.cameras.map((camera) => ({
      deviceId: camera.device_id,
      cameraId: camera.camera_id,
    })),
    total: data.total,
  };
}

/**
 * Get the URL for streaming a video
 */
export function getVideoUrl(deviceId: string, filename: string): string {
  return `${API_BASE}/devices/${deviceId}/videos/${encodeURIComponent(
    filename
  )}`;
}
