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
import { MermaidRenderer } from '../mermaid-renderer/mermaid-renderer';
import { MfeRenderer } from '../mfe-renderer/mfe-renderer';

import { MatTooltipModule } from '@angular/material/tooltip';

@Component({
    selector: 'app-chat-window',
    standalone: true,
    imports: [CommonModule, FormsModule, MatInputModule, MatButtonModule, MatIconModule, MatProgressSpinnerModule, MatTooltipModule, MarkdownPipe, MermaidRenderer, MfeRenderer],
    templateUrl: './chat-window.html',
    styleUrls: ['./chat-window.scss']
})
export class ChatWindow implements OnInit, AfterViewChecked, OnDestroy {
    messages: Message[] = [];
    newMessage: string = '';
    threadId: string | null = null;
    threadColor: string | null = null;
    currentStatusMsg: string | null = null;
    lastStatusUpdatedAtStr: string | null = null;
    stepStartTime: number | null = null;
    requestStartTime: number | null = null;
    currentStatusDuration: string | null = null;
    totalDuration: string | null = null;
    loading: boolean = false;
    sending: boolean = false;
    pollingSubscription?: Subscription;
    durationSubscription?: Subscription;
    externalMessageSub?: Subscription;
    pollCount: number = 0;
    pollingError: string | null = null;
    serverOffset: number = 0;

    @ViewChild('scrollContainer') private scrollContainer!: ElementRef;
    private lastScrollHeight = 0;
    private forceScroll = false;

    @ViewChild('messageInput') private messageInput!: ElementRef;

    constructor(
        private chatService: ChatService,
        private audioService: AudioService,
        private route: ActivatedRoute,
        private router: Router,
        private cdr: ChangeDetectorRef
    ) { }

    ngOnInit() {
        this.externalMessageSub = this.chatService.externalMessage$.subscribe(threadId => {
            if (this.threadId && this.threadId === threadId) {
                if (!this.sending) {
                    this.startPolling(this.threadId);
                }
            }
        });

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
        this.handleAutoScroll();
    }

    private handleAutoScroll() {
        if (!this.scrollContainer) return;
        const element = this.scrollContainer.nativeElement;
        const currentScrollHeight = element.scrollHeight;

        if (currentScrollHeight !== this.lastScrollHeight) {
            // Check if we were near bottom of the OLD height
            const position = element.scrollTop + element.clientHeight;
            const wasNearBottom = this.lastScrollHeight - position < 200;

            if (wasNearBottom || this.forceScroll) {
                element.scrollTop = currentScrollHeight;
                this.forceScroll = false;
            }
            this.lastScrollHeight = currentScrollHeight;
        }
    }

    ngOnDestroy() {
        this.stopPolling();
        if (this.externalMessageSub) {
            this.externalMessageSub.unsubscribe();
        }
    }

    scrollToBottom(force: boolean = false): void {
        if (force) {
            this.forceScroll = true;
            if (this.scrollContainer) {
                const element = this.scrollContainer.nativeElement;
                element.scrollTop = element.scrollHeight;
            }
        }
    }

    processMessages(rawMessages: Message[]): Message[] {
        const processed: Message[] = [];
        let currentAiGroup: Message | null = null;
        let aiMessagesGroup = [];

        for (const msg of rawMessages) {
            if (msg.type === 'human' || msg.type === 'error') {
                if (currentAiGroup) {
                    processed.push(currentAiGroup);
                    currentAiGroup = null;
                }
                processed.push(msg);
            } else {
                if (!currentAiGroup) {
                    // Start a new AI group
                    currentAiGroup = {
                        type: 'ai',
                        content: '',
                        additional_kwargs: {
                            tool_calls: []
                        },
                        usage_metadata: {
                            input_tokens: 0,
                            output_tokens: 0,
                            total_tokens: 0
                        }
                    };
                }

                if (msg.type === 'ai') {
                    // Update content if present (usually the last message has the final content)
                    if (msg.content) {
                        currentAiGroup.content = msg.content;
                    }

                    if (msg.additional_kwargs) {
                        // Merge tool calls
                        if (msg.additional_kwargs['tool_calls']) {
                            for (const tc of msg.additional_kwargs['tool_calls']) {
                                currentAiGroup.additional_kwargs!['tool_calls']!.push({...tc});
                            }
                        }
                        // Copy image url, questions
                        if (msg.additional_kwargs['image_url']) {
                            currentAiGroup.additional_kwargs!['image_url'] = msg.additional_kwargs['image_url'];
                        }
                        if (msg.additional_kwargs['follow_up_questions']) {
                            currentAiGroup.additional_kwargs!['follow_up_questions'] = msg.additional_kwargs['follow_up_questions'];
                        }
                    }

                    // Sum usage
                    if (msg.usage_metadata && currentAiGroup.usage_metadata) {
                        currentAiGroup.usage_metadata.input_tokens = (currentAiGroup.usage_metadata.input_tokens || 0) + (msg.usage_metadata.input_tokens || 0);
                        currentAiGroup.usage_metadata.output_tokens = (currentAiGroup.usage_metadata.output_tokens || 0) + (msg.usage_metadata.output_tokens || 0);
                        currentAiGroup.usage_metadata.total_tokens = (currentAiGroup.usage_metadata.total_tokens || 0) + (msg.usage_metadata.total_tokens || 0);
                        if (msg.usage_metadata.max_tokens) {
                            currentAiGroup.usage_metadata.max_tokens = msg.usage_metadata.max_tokens;
                        }
                    }

                    if (msg.duration) {
                        currentAiGroup.duration = msg.duration;
                    }

                } else if (msg.type === 'tool') {
                    // Find the tool call and attach the response
                    if (msg.tool_call_id && currentAiGroup.additional_kwargs?.['tool_calls']) {
                        const tc = currentAiGroup.additional_kwargs['tool_calls'].find(t => t.id === msg.tool_call_id);
                        if (tc) {
                            tc.response = msg.content;
                        }
                    }
                }
            }
        }

        if (currentAiGroup) {
            processed.push(currentAiGroup);
        }

        return processed;
    }

    loadHistory(threadId: string) {
        this.stopPolling();
        this.loading = true;
        this.cdr.detectChanges(); // Force update

        this.chatService.getHistory(threadId).subscribe({
            next: (res) => {
                this.threadColor = res.thread?.color || null;
                this.currentStatusMsg = res.thread?.status_msg || null;
                this.lastStatusUpdatedAtStr = res.thread?.status_updated_at || null;

                this.messages = this.processMessages(res.messages);

                this.loading = false;
                this.pollCount = 0;
                this.pollingError = null;

                if (res.thread?.current_server_time) {
                    this.serverOffset = Date.now() - new Date(res.thread.current_server_time).getTime();
                }

                if (this.messages.length > 0 && this.messages[this.messages.length - 1].type === 'human') {
                    const lastHumanMsg = this.messages[this.messages.length - 1];
                    this.requestStartTime = lastHumanMsg.created_at ? new Date(lastHumanMsg.created_at).getTime() + this.serverOffset : Date.now();
                    this.stepStartTime = this.lastStatusUpdatedAtStr ? new Date(this.lastStatusUpdatedAtStr).getTime() + this.serverOffset : Date.now();
                    this.startPolling(threadId);
                }

                this.scrollToBottom(true);
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

    sendSuggestedQuestion(question: string) {
        if (this.sending) return;
        this.newMessage = question;
        this.sendMessage();
    }

    sendMessage() {
        if (!this.newMessage.trim() || this.sending) return;

        const content = this.newMessage;
        this.newMessage = '';
        this.sending = true;
        this.pollCount = 0;
        this.pollingError = null;
        this.currentStatusMsg = null;
        this.lastStatusUpdatedAtStr = null;
        this.stepStartTime = Date.now();
        this.requestStartTime = Date.now();
        this.currentStatusDuration = '0.0s';
        this.totalDuration = '0.0s';

        this.audioService.playSendMessage();

        // Optimistic add
        this.messages.push({ type: 'human', content });
        this.scrollToBottom(true);

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
        this.durationSubscription = interval(1000).subscribe(() => {
            const now = Date.now();
            if (this.stepStartTime) {
                const diffMs = now - this.stepStartTime;
                const secs = Math.floor(diffMs / 1000);
                this.currentStatusDuration = `${secs}s`;
            }
            if (this.requestStartTime) {
                const diffMs = now - this.requestStartTime;
                const secs = Math.floor(diffMs / 1000);
                this.totalDuration = `${secs}s`;
            }
            this.cdr.detectChanges();
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

                if (res.thread?.current_server_time) {
                    this.serverOffset = Date.now() - new Date(res.thread.current_server_time).getTime();
                }

                const newUpdatedAtStr = res.thread?.status_updated_at || null;

                // If the updated at timestamp changed, reset our local parsing
                if (newUpdatedAtStr !== this.lastStatusUpdatedAtStr) {
                    this.lastStatusUpdatedAtStr = newUpdatedAtStr;
                    this.stepStartTime = newUpdatedAtStr ? new Date(newUpdatedAtStr).getTime() + this.serverOffset : Date.now();
                }

                const messages = this.processMessages(res.messages);

                // Preserve local durations
                for (let i = 0; i < messages.length; i++) {
                    if (this.messages[i] && this.messages[i].duration) {
                        messages[i].duration = this.messages[i].duration;
                    }
                }

                if (messages.length > 0) {
                    this.messages = messages;

                    const lastMsg = messages[messages.length - 1];

                    if (this.sending && !this.currentStatusMsg && this.pollCount > 1) {
                        if ((lastMsg.type === 'ai' || lastMsg.type === 'error')) {
                            if (this.totalDuration) {
                                lastMsg.duration = this.totalDuration;
                            }
                            this.stopPolling();
                            this.audioService.playBotReply();
                        } else if (lastMsg.type === 'tool') {
                            if (this.totalDuration) {
                                lastMsg.duration = this.totalDuration;
                            }
                            this.stopPolling();
                            this.audioService.playBotReply();
                        }
                    }

                    this.scrollToBottom();
                    this.cdr.detectChanges();
                    this.focusInput();
                }
            });
        });
    }

    handleMfeAction(event: {action: string, payload: any}, mfeId?: string) {
        if (!this.threadId) return;

        // Use ID if available, otherwise just say "inline MFE"
        const identifier = mfeId ? `MFE with ID: ${mfeId}` : 'inline MFE';
        const messageContent = `[System: User submitted data via ${event.action} action inside ${identifier}]\nData: ${JSON.stringify(event.payload, null, 2)}`;
        
        this.sending = true;
        this.chatService.sendMessage(messageContent, this.threadId).subscribe({
            next: () => {
                this.startPolling(this.threadId!);
            },
            error: (err) => {
                console.error('Error sending MFE action:', err);
                this.sending = false;
            }
        });
    }

    toggleTools(msg: Message) {
        msg.showTools = !msg.showTools;
    }

    stopPolling() {
        this.sending = false;
        this.pollCount = 0;
        this.pollingError = null;
        this.currentStatusMsg = null;
        this.lastStatusUpdatedAtStr = null;
        this.stepStartTime = null;
        this.requestStartTime = null;
        this.currentStatusDuration = null;
        this.totalDuration = null;

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
