import * as tus from 'tus-js-client';
import {
	supabase,
	supabaseUrl,
	supabaseAnonKey,
	bucket,
	uploadsTable
} from './supabase';

export type UploadStatus = 'queued' | 'uploading' | 'done' | 'failed';

export interface UploadItem {
	id: string;
	file: File;
	storagePath: string;
	status: UploadStatus;
	progress: number;
	error: string | null;
}

const RESUMABLE_THRESHOLD_BYTES = 6 * 1024 * 1024;
const TUS_CHUNK_SIZE = 6 * 1024 * 1024;
const MAX_CONCURRENT = 3;

function extensionFor(name: string): string {
	const dot = name.lastIndexOf('.');
	return dot >= 0 ? name.slice(dot) : '';
}

class UploadQueue {
	items = $state<UploadItem[]>([]);

	addFiles(files: FileList | File[]): void {
		for (const file of Array.from(files)) {
			const id = crypto.randomUUID();
			this.items.push({
				id,
				file,
				storagePath: `${id}${extensionFor(file.name)}`,
				status: 'queued',
				progress: 0,
				error: null
			});
		}
		this.pump();
	}

	retry(id: string): void {
		const item = this.items.find((i) => i.id === id);
		if (!item || item.status !== 'failed') return;
		item.status = 'queued';
		item.error = null;
		item.progress = 0;
		this.pump();
	}

	clearDone(): void {
		this.items = this.items.filter((i) => i.status !== 'done');
	}

	get allDone(): boolean {
		return this.items.length > 0 && this.items.every((i) => i.status === 'done');
	}

	get anyActive(): boolean {
		return this.items.some((i) => i.status === 'queued' || i.status === 'uploading');
	}

	private pump(): void {
		const active = this.items.filter((i) => i.status === 'uploading').length;
		if (active >= MAX_CONCURRENT) return;
		const next = this.items.find((i) => i.status === 'queued');
		if (!next) return;
		next.status = 'uploading';
		this.runOne(next).finally(() => this.pump());
		this.pump();
	}

	private async runOne(item: UploadItem): Promise<void> {
		try {
			if (item.file.size >= RESUMABLE_THRESHOLD_BYTES) {
				await uploadResumable(item);
			} else {
				await uploadStandard(item);
			}
			await recordRow(item);
			item.progress = 1;
			item.status = 'done';
		} catch (err) {
			item.status = 'failed';
			item.error = err instanceof Error ? err.message : String(err);
		}
	}
}

// Storage uploads require the legacy JWT anon key in Authorization (the route
// schema-requires the header, and the JWT decoder rejects non-JWT publishable
// keys). apikey is sent alongside so the call is also valid for clients/SDKs
// that auth via that path.
function uploadResumable(item: UploadItem): Promise<void> {
	return new Promise((resolve, reject) => {
		const upload = new tus.Upload(item.file, {
			endpoint: `${supabaseUrl}/storage/v1/upload/resumable`,
			retryDelays: [0, 3000, 5000, 10000, 20000],
			// No x-upsert: paths are UUIDs so there's no conflict to resolve,
			// and `INSERT ... ON CONFLICT DO UPDATE` would force RLS to also
			// evaluate UPDATE policies — which we don't want anon to have.
			headers: {
				authorization: `Bearer ${supabaseAnonKey}`,
				apikey: supabaseAnonKey
			},
			uploadDataDuringCreation: true,
			removeFingerprintOnSuccess: true,
			chunkSize: TUS_CHUNK_SIZE,
			metadata: {
				bucketName: bucket,
				objectName: item.storagePath,
				contentType: item.file.type || 'application/octet-stream',
				cacheControl: '3600'
			},
			onError: (err) => reject(err),
			onProgress: (bytesUploaded, bytesTotal) => {
				item.progress = bytesTotal > 0 ? bytesUploaded / bytesTotal : 0;
			},
			onSuccess: () => resolve()
		});
		upload
			.findPreviousUploads()
			.then((prev) => {
				if (prev.length > 0) upload.resumeFromPreviousUpload(prev[0]);
				upload.start();
			})
			.catch(reject);
	});
}

function uploadStandard(item: UploadItem): Promise<void> {
	return new Promise((resolve, reject) => {
		const xhr = new XMLHttpRequest();
		const url = `${supabaseUrl}/storage/v1/object/${bucket}/${item.storagePath}`;
		xhr.open('POST', url);
		xhr.setRequestHeader('authorization', `Bearer ${supabaseAnonKey}`);
		xhr.setRequestHeader('apikey', supabaseAnonKey);
		if (item.file.type) xhr.setRequestHeader('content-type', item.file.type);
		xhr.upload.onprogress = (e) => {
			if (e.lengthComputable) item.progress = e.loaded / e.total;
		};
		xhr.onload = () => {
			if (xhr.status >= 200 && xhr.status < 300) resolve();
			else reject(new Error(`Upload failed (${xhr.status}): ${xhr.responseText || 'no body'}`));
		};
		xhr.onerror = () => reject(new Error('Network error during upload'));
		xhr.send(item.file);
	});
}

async function recordRow(item: UploadItem): Promise<void> {
	const { error } = await supabase.from(uploadsTable).insert({
		storage_path: item.storagePath,
		original_name: item.file.name,
		content_type: item.file.type || null,
		size_bytes: item.file.size
	});
	if (error) throw new Error(`Database insert failed: ${error.message}`);
}

export const uploads = new UploadQueue();
