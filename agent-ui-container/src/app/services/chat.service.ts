import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject, map, shareReplay, switchMap } from 'rxjs';
import { AuthService } from './auth.service';

export interface Thread {
  thread_id: string;
  user_id: string;
  title: string;
  created_at?: string;
  color?: string;
  status_msg?: string;
  status_updated_at?: string;
  current_server_time?: string;
}

export interface ChatResponse {
  thread_id: string;
  response?: string;
  status?: string;
}

export interface Message {
  type: string;
  content: string;
  duration?: string;
  created_at?: string;
  usage_metadata?: {
    input_tokens?: number;
    output_tokens?: number;
    total_tokens?: number;
    max_tokens?: number;
  };
  additional_kwargs?: {
    image_url?: string;
    [key: string]: any;
  };
}

export interface HistoryResponse {
  thread?: Thread;
  messages: Message[];
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private apiUrl$: Observable<string>;

  constructor(private http: HttpClient, private authService: AuthService) {
    const basePath = new URL('./', import.meta.url).href;
    this.apiUrl$ = this.http.get<{ apiUrl: string }>(`${basePath}assets/contents/config.json`).pipe(
      map(config => config.apiUrl),
      shareReplay(1)
    );
  }

  private getHeaders(): HttpHeaders {
    const userId = this.authService.getUserId() || '';
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'X-User-ID': userId
    });
  }

  private threadsSubject = new BehaviorSubject<Thread[]>([]);
  threads$ = this.threadsSubject.asObservable();

  refreshThreads() {
    this.getThreads().subscribe({
      next: (res) => {
        this.threadsSubject.next(res.threads);
      },
      error: (err) => console.error('Error refreshing threads', err)
    });
  }

  sendMessage(message: string, threadId?: string): Observable<ChatResponse> {
    return this.apiUrl$.pipe(
      switchMap(apiUrl => this.http.post<ChatResponse>(`${apiUrl}/chat`, { message, thread_id: threadId }, { headers: this.getHeaders() }))
    );
  }

  getThreads(): Observable<{ threads: Thread[] }> {
    return this.apiUrl$.pipe(
      switchMap(apiUrl => this.http.get<{ threads: Thread[] }>(`${apiUrl}/threads`, { headers: this.getHeaders() }))
    );
  }

  getHistory(threadId: string): Observable<HistoryResponse> {
    return this.apiUrl$.pipe(
      switchMap(apiUrl => this.http.get<HistoryResponse>(`${apiUrl}/threads/${threadId}/history`, { headers: this.getHeaders() }))
    );
  }

  deleteThread(threadId: string): Observable<any> {
    return this.apiUrl$.pipe(
      switchMap(apiUrl => this.http.delete(`${apiUrl}/threads/${threadId}`, { headers: this.getHeaders() }))
    );
  }

  updateThread(threadId: string, updates: Partial<Thread>): Observable<any> {
    return this.apiUrl$.pipe(
      switchMap(apiUrl => this.http.patch(`${apiUrl}/threads/${threadId}`, updates, { headers: this.getHeaders() }))
    );
  }
}
