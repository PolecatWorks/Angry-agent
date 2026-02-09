import { Component, OnInit, ViewChild, ElementRef, AfterViewChecked, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ActivatedRoute, Router } from '@angular/router';
import { ChatService, Message } from '../../services/chat.service';

@Component({
    selector: 'app-chat-window',
    standalone: true,
    imports: [CommonModule, FormsModule, MatInputModule, MatButtonModule, MatIconModule, MatProgressSpinnerModule],
    templateUrl: './chat-window.html',
    styleUrls: ['./chat-window.scss']
})
export class ChatWindow implements OnInit, AfterViewChecked {
    messages: Message[] = [];
    newMessage: string = '';
    threadId: string | null = null;
    loading: boolean = false;
    sending: boolean = false;

    @ViewChild('scrollContainer') private scrollContainer!: ElementRef;

    @ViewChild('messageInput') private messageInput!: ElementRef;

    constructor(
        private chatService: ChatService,
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
            }
        });
    }

    ngAfterViewChecked() {
        this.scrollToBottom();
    }

    scrollToBottom(): void {
        try {
            this.scrollContainer.nativeElement.scrollTop = this.scrollContainer.nativeElement.scrollHeight;
        } catch (err) { }
    }

    loadHistory(threadId: string) {
        this.loading = true;
        this.cdr.detectChanges(); // Force update

        this.chatService.getHistory(threadId).subscribe({
            next: (res) => {
                this.messages = res.messages;
                this.loading = false;
                this.scrollToBottom();
                this.cdr.detectChanges();
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
        }, 0);
    }

    sendMessage() {
        if (!this.newMessage.trim()) return;

        const content = this.newMessage;
        this.newMessage = '';
        this.sending = true;

        // Optimistic add
        this.messages.push({ type: 'human', content });
        this.scrollToBottom();

        this.chatService.sendMessage(content, this.threadId || undefined).subscribe({
            next: (res) => {
                // If new chat, navigate to URL with threadId
                if (!this.threadId) {
                    this.threadId = res.thread_id;
                    // Note: The router navigation will trigger ngOnInit.
                    // We rely on the check there to preserve these messages.
                    this.messages.push({ type: 'ai', content: res.response });
                    this.router.navigate(['/chat', this.threadId]);
                    this.chatService.notifyThreadCreated();
                } else {
                    this.messages.push({ type: 'ai', content: res.response });
                    this.scrollToBottom();
                }
                this.sending = false;
                this.cdr.detectChanges();
                this.focusInput();
            },
            error: (err) => {
                console.error('Error sending message:', err);
                this.messages.push({ type: 'error', content: 'Failed to send message' });
                this.sending = false;
                this.cdr.detectChanges();
                this.focusInput();
            }
        });
    }
}
