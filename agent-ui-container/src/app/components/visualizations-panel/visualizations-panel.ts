import { Component, Input, OnInit, OnDestroy, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ChatService, Visualization, JsonPatchOp, CanvasSelection } from '../../services/chat.service';
import { MfeRenderer } from '../mfe-renderer/mfe-renderer';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-visualizations-panel',
  standalone: true,
  imports: [CommonModule, MatProgressSpinnerModule, MfeRenderer],
  templateUrl: './visualizations-panel.html',
  styleUrls: ['./visualizations-panel.scss']
})
export class VisualizationsPanel implements OnInit, OnDestroy, OnChanges {
  @Input() threadId: string | null = null;
  @Input() isThreadActive: boolean = false;

  visualizations: Visualization[] = [];
  loading: boolean = false;
  showJsonIds: Set<string> = new Set<string>();
  private pollSubscription?: Subscription;
  private stateSyncTimers = new Map<string, any>();

  constructor(private chatService: ChatService) {}

  ngOnInit() {
    this.startPolling();
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['threadId']) {
      this.visualizations = [];
      this.restartPolling();
    }
  }

  ngOnDestroy() {
    this.stopPolling();
    for (const timer of this.stateSyncTimers.values()) {
      clearTimeout(timer);
    }
    this.stateSyncTimers.clear();
  }

  trackByVizId(index: number, viz: Visualization): string {
    return viz.id;
  }

  private restartPolling() {
    this.stopPolling();
    this.showJsonIds.clear();
    this.startPolling();
  }

  private startPolling() {
    if (!this.threadId) return;

    if (this.visualizations.length === 0) {
      Promise.resolve().then(() => this.loading = true);
    }

    this.pollSubscription = this.chatService.currentVisualizations$.subscribe((visualizations) => {
      this.visualizations = visualizations || [];
      Promise.resolve().then(() => this.loading = false);
    });
  }

  private stopPolling() {
    if (this.pollSubscription) {
      this.pollSubscription.unsubscribe();
      this.pollSubscription = undefined;
    }
  }

  toggleJsonView(id: string) {
    if (this.showJsonIds.has(id)) {
      this.showJsonIds.delete(id);
    } else {
      this.showJsonIds.add(id);
    }
  }

  isJsonView(id: string): boolean {
    return this.showJsonIds.has(id);
  }

  getFormattedJson(viz: Visualization): string {
    return JSON.stringify(viz, null, 2);
  }

  /**
   * Silent human state sync: updates the visualization state in the backend
   * (debounced 300ms) WITHOUT injecting a synthetic chat message or triggering an LLM turn.
   */
  handleMfeStateChange(event: { state: any; patches: JsonPatchOp[] }, vizId: string) {
    if (!this.threadId) return;

    const viz = this.visualizations.find((v) => v.id === vizId);
    if (viz) {
      viz.content = event.state;
    }

    const existingTimer = this.stateSyncTimers.get(vizId);
    if (existingTimer) {
      clearTimeout(existingTimer);
    }

    const threadId = this.threadId;
    const timer = setTimeout(() => {
      this.stateSyncTimers.delete(vizId);
      this.chatService.patchVisualizationState(threadId, vizId, event.state, event.patches).subscribe({
        error: (err) => console.error('Error syncing live MFE state:', err)
      });
    }, 300);

    this.stateSyncTimers.set(vizId, timer);
  }

  /**
   * Point-and-Ask focus tracking: forwards the user's currently focused MFE field/row
   * to ChatService so ChatWindow can display a focus pill and include it in POST /api/chat.
   */
  handleMfeSelectionChange(selection: CanvasSelection | null, vizId: string) {
    if (selection) {
      this.chatService.setActiveSelection({
        ...selection,
        canvasId: vizId
      });
    } else {
      this.chatService.setActiveSelection(null);
    }
  }

  handleMfeAction(event: { action: string; payload: any }, vizId: string) {
    if (!this.threadId) return;
    
    // Format the payload as a string that the LLM can easily understand including the visualization ID
    const messageContent = `[System: User submitted data via ${event.action} action inside visualization MFE with ID: ${vizId}]\nData: ${JSON.stringify(event.payload, null, 2)}`;
    
    this.chatService.sendMessage(messageContent, this.threadId).subscribe({
      next: () => {
        console.log('Successfully sent MFE action to chat');
        this.chatService.triggerExternalMessage(this.threadId!);
      },
      error: (err) => console.error('Error sending MFE action:', err)
    });
  }
}
