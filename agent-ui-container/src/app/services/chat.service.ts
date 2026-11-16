import { Injectable, Optional } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject, map, shareReplay, switchMap, tap } from 'rxjs';
import { AuthService } from './auth.service';

export interface JsonPatchOp {
  op: 'add' | 'replace' | 'remove';
  path: string;
  value?: any;
}

export interface AiFieldAttribution {
  path: string;
  source: 'ai' | 'user';
  confidence?: number;
  rationale?: string;
  epistemic_status?: string;
}

export interface CanvasSelection {
  canvasId: string;
  path: string;
  id?: string;
  label: string;
  context?: any;
}

export interface MfeCanvasController<T = any> {
  applyPatch(patches: JsonPatchOp[] | Partial<T>, attributions?: AiFieldAttribution[]): void;
  getState(): T;
  getSchema(): Record<string, any>;
  unmount(): void;
}

export interface CanvasVisualizationSnapshot {
  id: string;
  state: any;
  json_schema?: Record<string, any>;
}

export interface CanvasContextPayload {
  visualizations: CanvasVisualizationSnapshot[];
  active_selection?: {
    canvas_id: string;
    path: string;
    id?: string;
    label: string;
    context?: any;
  } | null;
}

export interface Thread {
  thread_id: string;
  user_id: string;
  title: string;
  created_at?: string;
  color?: string;
  status_msg?: string;
  status_updated_at?: string;
  current_server_time?: string;
  learning_mode_enabled?: boolean;
}

export interface UserSettings {
  learning_mode_enabled: boolean;
}

export interface AgentDefinition {
  id?: string;
  name: string;
  content: string;
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
  name?: string;
  tool_call_id?: string;
  usage_metadata?: {
    input_tokens?: number;
    output_tokens?: number;
    total_tokens?: number;
    max_tokens?: number;
  };
  additional_kwargs?: {
    image_url?: string;
    follow_up_questions?: string[];
    tool_calls?: { id?: string; name: string; args: any; response?: string }[];
    [key: string]: any;
  };
  showTools?: boolean;
}

export interface HistoryResponse {
  thread?: Thread;
  messages: Message[];
  visualizations?: Visualization[];
}

export interface Visualization {
  id: string;
  thread_id: string;
  provider: string;
  component: string;
  content: any;
  name?: string;
  title?: string;
  description?: string;
  order_index: number;
  json_schema?: Record<string, any>;
  attributions?: AiFieldAttribution[];
  created_at?: string;
  updated_at?: string;
}

export interface VisualizationsResponse {
  visualizations: Visualization[];
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private apiUrl$: Observable<string>;
  private canvasControllers = new Map<string, MfeCanvasController>();

  private activeSelectionSubject = new BehaviorSubject<CanvasSelection | null>(null);
  activeSelection$ = this.activeSelectionSubject.asObservable();

  constructor(private http: HttpClient, private authService: AuthService) {
    let configPath = "/assets/contents/config.json";
    try {
      const rel = ["assets", "contents", "config.json"].join("/");
      const base = new URL(rel, import.meta.url).href;
      if (!base.includes("/@fs/") && !base.includes("/@vite/")) {
        configPath = base;
      }
    } catch {
      configPath = "/assets/contents/config.json";
    }
    this.apiUrl$ = this.http.get<{ apiUrl: string }>(configPath).pipe(
      map(config => (config.apiUrl ? config.apiUrl.replace(/\/+$/, '') : '')),
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

  private externalMessageSubject = new Subject<string>();
  externalMessage$ = this.externalMessageSubject.asObservable();

  triggerExternalMessage(threadId: string) {
    this.externalMessageSubject.next(threadId);
  }

  private currentVisualizationsSubject = new BehaviorSubject<Visualization[]>([]);
  currentVisualizations$ = this.currentVisualizationsSubject.asObservable();

  updateVisualizations(visualizations: Visualization[]) {
    this.currentVisualizationsSubject.next(visualizations);
  }

  registerCanvasController(id: string, controller: MfeCanvasController) {
    if (!id) return;
    this.canvasControllers.set(id, controller);
  }

  unregisterCanvasController(id: string) {
    if (!id) return;
    this.canvasControllers.delete(id);
    const currentSel = this.activeSelectionSubject.getValue();
    if (currentSel && currentSel.canvasId === id) {
      this.activeSelectionSubject.next(null);
    }
  }

  setActiveSelection(selection: CanvasSelection | null) {
    this.activeSelectionSubject.next(selection);
  }

  getActiveSelection(): CanvasSelection | null {
    return this.activeSelectionSubject.getValue();
  }

  getCanvasContext(): CanvasContextPayload | undefined {
    const vizSnapshots: CanvasVisualizationSnapshot[] = [];
    for (const [id, ctrl] of this.canvasControllers.entries()) {
      try {
        vizSnapshots.push({
          id,
          state: ctrl.getState(),
          json_schema: ctrl.getSchema()
        });
      } catch (e) {
        console.warn(`Failed to read state/schema from canvas controller ${id}`, e);
      }
    }

    const activeSel = this.activeSelectionSubject.getValue();
    if (vizSnapshots.length === 0 && !activeSel) {
      return undefined;
    }

    return {
      visualizations: vizSnapshots,
      active_selection: activeSel
        ? {
            canvas_id: activeSel.canvasId,
            path: activeSel.path,
            id: activeSel.id,
            label: activeSel.label,
            context: activeSel.context
          }
        : null
    };
  }

  patchVisualizationState(
    threadId: string,
    vizId: string,
    content: any,
    patches: JsonPatchOp[] = [],
    jsonSchema?: Record<string, any>
  ): Observable<any> {
    const activeSel = this.activeSelectionSubject.getValue();
    const payload: Record<string, any> = {
      content,
      patches
    };
    if (jsonSchema) {
      payload['json_schema'] = jsonSchema;
    }
    if (activeSel && activeSel.canvasId === vizId) {
      payload['active_selection'] = {
        canvas_id: activeSel.canvasId,
        path: activeSel.path,
        id: activeSel.id,
        label: activeSel.label,
        context: activeSel.context
      };
    }

    return this.apiUrl$.pipe(
      switchMap(apiUrl =>
        this.http.patch(`${apiUrl}/threads/${threadId}/visualizations/${vizId}`, payload, {
          headers: this.getHeaders()
        })
      )
    );
  }

  refreshThreads() {
    this.getThreads().subscribe({
      next: (res) => {
        this.threadsSubject.next(res.threads);
      },
      error: (err) => console.error('Error refreshing threads', err)
    });
  }

  sendMessage(message: string, threadId?: string, bypassLearningMode: boolean = false): Observable<ChatResponse> {
    const body: Record<string, any> = {
      message,
      thread_id: threadId,
      bypass_learning_mode: bypassLearningMode
    };
    const canvasContext = this.getCanvasContext();
    if (canvasContext) {
      body['canvas_context'] = canvasContext;
    }

    return this.apiUrl$.pipe(
      switchMap(apiUrl => this.http.post<ChatResponse>(`${apiUrl}/chat`, body, { headers: this.getHeaders() }))
    );
  }

  getThreads(): Observable<{ threads: Thread[] }> {
    return this.apiUrl$.pipe(
      switchMap(apiUrl => this.http.get<{ threads: Thread[] }>(`${apiUrl}/threads`, { headers: this.getHeaders() }))
    );
  }

  getHistory(threadId: string): Observable<HistoryResponse> {
    return this.apiUrl$.pipe(
      switchMap(apiUrl => this.http.get<HistoryResponse>(`${apiUrl}/threads/${threadId}/history`, { headers: this.getHeaders() })),
      tap((res) => {
        if (res.visualizations) {
          this.updateVisualizations(res.visualizations);
        }
        if (res.thread) {
          const currentThreads = this.threadsSubject.getValue();
          const threadIndex = currentThreads.findIndex(t => t.thread_id === res.thread?.thread_id);
          if (threadIndex !== -1) {
            const updatedThreads = [...currentThreads];
            updatedThreads[threadIndex] = { ...updatedThreads[threadIndex], ...res.thread };
            this.threadsSubject.next(updatedThreads);
          }
        }
      })
    );
  }

  deleteThread(threadId: string): Observable<any> {
    return this.apiUrl$.pipe(
      switchMap(apiUrl => this.http.delete(`${apiUrl}/threads/${threadId}`, { headers: this.getHeaders() }))
    );
  }

  updateThread(threadId: string, thread: { title?: string, color?: string, learning_mode_enabled?: boolean }): Observable<any> {
    return this.apiUrl$.pipe(
      switchMap(apiUrl => this.http.put(`${apiUrl}/threads/${threadId}`, thread, { headers: this.getHeaders() }))
    );
  }

  getVisualizations(threadId: string): Observable<VisualizationsResponse> {
    return this.apiUrl$.pipe(
      switchMap(apiUrl => this.http.get<VisualizationsResponse>(`${apiUrl}/threads/${threadId}/visualizations`, { headers: this.getHeaders() }))
    );
  }

  getUserSettings(): Observable<UserSettings> {
    return this.apiUrl$.pipe(
      switchMap(apiUrl => this.http.get<UserSettings>(`${apiUrl}/user/settings`, { headers: this.getHeaders() }))
    );
  }

  updateUserSettings(settings: UserSettings): Observable<any> {
    return this.apiUrl$.pipe(
      switchMap(apiUrl => this.http.put(`${apiUrl}/user/settings`, settings, { headers: this.getHeaders() }))
    );
  }

  getAgents(): Observable<AgentDefinition[]> {
    return this.apiUrl$.pipe(
      switchMap(apiUrl => this.http.get<AgentDefinition[]>(`${apiUrl}/agents`, { headers: this.getHeaders() }))
    );
  }

  createAgent(agent: AgentDefinition): Observable<AgentDefinition> {
    return this.apiUrl$.pipe(
      switchMap(apiUrl => this.http.post<AgentDefinition>(`${apiUrl}/agents`, agent, { headers: this.getHeaders() }))
    );
  }

  updateAgent(id: string, agent: AgentDefinition): Observable<AgentDefinition> {
    return this.apiUrl$.pipe(
      switchMap(apiUrl => this.http.put<AgentDefinition>(`${apiUrl}/agents/${id}`, agent, { headers: this.getHeaders() }))
    );
  }

  deleteAgent(id: string): Observable<any> {
    return this.apiUrl$.pipe(
      switchMap(apiUrl => this.http.delete(`${apiUrl}/agents/${id}`, { headers: this.getHeaders() }))
    );
  }
}
