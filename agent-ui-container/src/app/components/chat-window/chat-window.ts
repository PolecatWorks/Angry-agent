import { Component, OnInit, ViewChild, ElementRef, AfterViewChecked, ChangeDetectorRef, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ActivatedRoute, Router } from '@angular/router';
import { ChatService, Message } from '../../services/chat.service';
import { AudioService } from '../../services/audio.service';
import { MarkdownPipe } from '../../pipes/markdown.pipe';
import { interval, Subscription, of } from 'rxjs';
import { catchError } from 'rxjs/operators';

@Component({
    selector: 'app-chat-window',
    standalone: true,
    imports: [CommonModule, FormsModule, MatInputModule, MatButtonModule, MatIconModule, MatProgressSpinnerModule, MarkdownPipe],
    templateUrl: './chat-window.html',
    styleUrls: ['./chat-window.scss']
})
export class ChatWindow implements OnInit, AfterViewChecked, OnDestroy {
    messages: Message[] = [];
    newMessage: string = '';
    threadId: string | null = null;
    threadColor: string | null = null;
    currentStatusMsg: string | null = null;
    statusUpdatedAt: Date | null = null;
    currentStatusDuration: string | null = null;
    loading: boolean = false;
    sending: boolean = false;
    pollingSubscription?: Subscription;
    durationSubscription?: Subscription;
    pollCount: number = 0;
    pollingError: string | null = null;

    @ViewChild('scrollContainer') private scrollContainer!: ElementRef;

    @ViewChild('messageInput') private messageInput!: ElementRef;

    constructor(
        private chatService: ChatService,
        private audioService: AudioService,
        private route: ActivatedRoute,
        private router: Router,
        private cdr: ChangeDetectorRef
    ) { }

    ngOnInit() {
        this.route.paramMap.subscribe(params => {
            const newThreadId = params.get('threadId');

            // If we are navigating to the same thread we just created/updated and have messages, don't reload
            if (newThreadId && newThreadId === this.threadId && this.messages.length > 0) {
                return;
            }

            this.threadId = newThreadId;
            this.messages = [];

            if (this.threadId) {
                this.loadHistory(this.threadId);
            } else {
                this.loading = false;
                this.focusInput();
            }
        });
    }

    ngAfterViewChecked() {
        this.scrollToBottom();
    }

    ngOnDestroy() {
        this.stopPolling();
    }

    scrollToBottom(): void {
        try {
            this.scrollContainer.nativeElement.scrollTop = this.scrollContainer.nativeElement.scrollHeight;
        } catch (err) { }
    }

    loadHistory(threadId: string) {
        this.stopPolling();
        this.loading = true;
        this.cdr.detectChanges(); // Force update

        this.chatService.getHistory(threadId).subscribe({
            next: (res) => {
                this.threadColor = res.thread?.color || null;
                this.currentStatusMsg = res.thread?.status_msg || null;
                this.statusUpdatedAt = res.thread?.status_updated_at ? new Date(res.thread.status_updated_at) : null;
                this.messages = res.messages;
                this.loading = false;
                this.pollCount = 0;
                this.pollingError = null;

                if (this.messages.length > 0 && this.messages[this.messages.length - 1].type === 'human') {
                    this.startPolling(threadId);
                }

                this.scrollToBottom();
                this.cdr.detectChanges();
                this.focusInput();
            },
            error: (err) => {
                console.error('Error loading history:', err);
                this.loading = false;
                this.cdr.detectChanges();
            }
        });
    }

    focusInput() {
        setTimeout(() => {
            if (this.messageInput) {
                this.messageInput.nativeElement.focus();
            }
        }, 100);
    }

    sendMessage() {
        if (!this.newMessage.trim() || this.sending) return;

        const content = this.newMessage;
        this.newMessage = '';
        this.sending = true;
        this.pollCount = 0;
        this.pollingError = null;
        this.currentStatusMsg = null;
        this.statusUpdatedAt = null;
        this.currentStatusDuration = null;

        this.audioService.playSendMessage();

        // Optimistic add
        this.messages.push({ type: 'human', content });
        this.scrollToBottom();

        this.chatService.sendMessage(content, this.threadId || undefined).subscribe({
            next: (res) => {
                if (!this.threadId) {
                    this.threadId = res.thread_id;
                    this.router.navigate(['../chat', this.threadId], { relativeTo: this.route });
                    this.chatService.refreshThreads();
                }
                this.startPolling(res.thread_id);
            },
            error: (err) => {
                console.error('Error sending message:', err);
                this.messages.push({ type: 'error', content: 'Failed to send message' });
                this.stopPolling();
                this.cdr.detectChanges();
                this.focusInput();
            }
        });
    }

    startDurationTimer() {
        if (this.durationSubscription && !this.durationSubscription.closed) {
            return;
        }
        this.durationSubscription = interval(100).subscribe(() => {
            if (this.statusUpdatedAt) {
                const now = new Date();
                const diffMs = now.getTime() - this.statusUpdatedAt.getTime();
                if (diffMs > 0) {
                    const secs = Math.floor(diffMs / 1000);
                    const tens = Math.floor((diffMs % 1000) / 100);
                    this.currentStatusDuration = `${secs}.${tens}s`;
                    this.cdr.detectChanges();
                }
            } else {
                this.currentStatusDuration = null;
            }
        });
    }

    startPolling(threadId: string) {
        if (this.pollingSubscription && !this.pollingSubscription.closed) {
            return;
        }
        this.sending = true;
        this.pollCount = 0;
        this.pollingError = null;
        this.startDurationTimer();

        this.pollingSubscription = interval(2000).subscribe(() => {
            this.pollCount++;
            this.chatService.getHistory(threadId).pipe(
                catchError(err => {
                    console.error('Error polling history:', err);
                    this.pollingError = 'Connection failed, retrying...';
                    this.cdr.detectChanges();
                    return of(null);
                })
            ).subscribe(res => {
                if (!res) return; // Request failed, wait for next tick

                this.pollingError = null;
                this.currentStatusMsg = res.thread?.status_msg || null;

                const newUpdatedAt = res.thread?.status_updated_at ? new Date(res.thread.status_updated_at) : null;

                // If the updated at timestamp changed, reset our local parsing
                if (newUpdatedAt?.getTime() !== this.statusUpdatedAt?.getTime()) {
                    this.statusUpdatedAt = newUpdatedAt;
                }

                const messages = res.messages;
                if (messages.length > 0) {
                    const lastMsg = messages[messages.length - 1];
                    if (lastMsg.type === 'ai' || lastMsg.type === 'error') {
                        this.messages = messages;
                        this.stopPolling();
                        this.audioService.playBotReply();
                        this.scrollToBottom();
                        this.cdr.detectChanges();
                        this.focusInput();
                    } else {
                        this.cdr.detectChanges();
                    }
                }
            });
        });
    }

    stopPolling() {
        this.sending = false;
        this.pollCount = 0;
        this.pollingError = null;
        this.currentStatusMsg = null;
        this.statusUpdatedAt = null;
        this.currentStatusDuration = null;

        if (this.pollingSubscription) {
            this.pollingSubscription.unsubscribe();
            this.pollingSubscription = undefined;
        }
        if (this.durationSubscription) {
            this.durationSubscription.unsubscribe();
            this.durationSubscription = undefined;
        }
    }
}
