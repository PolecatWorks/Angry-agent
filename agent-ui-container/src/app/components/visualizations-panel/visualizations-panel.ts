import { Component, Input, OnInit, OnDestroy, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ChatService, Visualization } from '../../services/chat.service';
import { MfeRenderer } from '../mfe-renderer/mfe-renderer';
import { Subscription, interval, of } from 'rxjs';
import { switchMap, startWith, catchError, filter } from 'rxjs/operators';

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
  private pollSubscription?: Subscription;

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
  }

  private restartPolling() {
    this.stopPolling();
    this.startPolling();
  }

  private startPolling() {
    if (!this.threadId) return;

    if (this.visualizations.length === 0) {
      Promise.resolve().then(() => this.loading = true);
    }

    this.pollSubscription = interval(3000).pipe(
      startWith(0),
      filter(() => !!this.threadId),
      switchMap(() => this.chatService.getVisualizations(this.threadId!).pipe(
        catchError(err => {
          console.error('Error fetching visualizations:', err);
          return of({ visualizations: [] }); // Continue polling on error
        })
      ))
    ).subscribe((res: any) => {
      this.visualizations = res.visualizations;
      Promise.resolve().then(() => this.loading = false);
    });
  }

  private stopPolling() {
    if (this.pollSubscription) {
      this.pollSubscription.unsubscribe();
      this.pollSubscription = undefined;
    }
  }

  handleMfeAction(event: {action: string, payload: any}) {
    if (!this.threadId) return;
    
    // Format the payload as a string that the LLM can easily understand
    const messageContent = `[System: User submitted data via ${event.action} action inside the MFE visualization pane]\nData: ${JSON.stringify(event.payload, null, 2)}`;
    
    this.chatService.sendMessage(messageContent, this.threadId).subscribe({
      next: () => {
        console.log('Successfully sent MFE action to chat');
        this.chatService.triggerExternalMessage(this.threadId!);
      },
      error: (err) => console.error('Error sending MFE action:', err)
    });
  }
}
