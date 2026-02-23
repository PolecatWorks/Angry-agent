import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { AuthService } from './auth.service';

export interface Thread {
  thread_id: string;
  user_id: string;
  title: string;
  created_at?: string;
  color?: string;
}

export interface ChatResponse {
  thread_id: string;
  response: string;
}

export interface Message {
  type: string;
  content: string;
}

export interface HistoryResponse {
  thread?: Thread;
  messages: Message[];
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private apiUrl = 'http://localhost:8080/api';

  constructor(private http: HttpClient, private authService: AuthService) { }

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
    return this.http.post<ChatResponse>(`${this.apiUrl}/chat`, { message, thread_id: threadId }, { headers: this.getHeaders() });
  }

  getThreads(): Observable<{ threads: Thread[] }> {
    return this.http.get<{ threads: Thread[] }>(`${this.apiUrl}/threads`, { headers: this.getHeaders() });
  }

  getHistory(threadId: string): Observable<HistoryResponse> {
    return this.http.get<HistoryResponse>(`${this.apiUrl}/threads/${threadId}/history`, { headers: this.getHeaders() });
  }

  deleteThread(threadId: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/threads/${threadId}`, { headers: this.getHeaders() });
  }

  updateThreadColor(threadId: string, color: string): Observable<any> {
    return this.http.patch(`${this.apiUrl}/threads/${threadId}/color`, { color }, { headers: this.getHeaders() });
  }
}
