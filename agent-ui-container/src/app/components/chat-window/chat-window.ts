import { Component, OnInit, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
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

  constructor(
      private chatService: ChatService,
      private route: ActivatedRoute,
      private router: Router
  ) {}

  ngOnInit() {
    this.route.paramMap.subscribe(params => {
        this.threadId = params.get('threadId');
        this.messages = [];
        if (this.threadId) {
            this.loadHistory(this.threadId);
        }
    });
  }

  ngAfterViewChecked() {
      this.scrollToBottom();
  }

  scrollToBottom(): void {
      try {
          this.scrollContainer.nativeElement.scrollTop = this.scrollContainer.nativeElement.scrollHeight;
      } catch(err) { }
  }

  loadHistory(threadId: string) {
      this.loading = true;
      this.chatService.getHistory(threadId).subscribe({
          next: (res) => {
              this.messages = res.messages;
              this.loading = false;
              this.scrollToBottom();
          },
          error: (err) => {
              console.error(err);
              this.loading = false;
          }
      });
  }

  sendMessage() {
      if (!this.newMessage.trim()) return;

      const content = this.newMessage;
      this.newMessage = '';
      this.sending = true;

      // Optimistic add
      this.messages.push({ type: 'human', content });

      this.chatService.sendMessage(content, this.threadId || undefined).subscribe({
          next: (res) => {
              // If new chat, navigate to URL with threadId
              if (!this.threadId) {
                  this.threadId = res.thread_id;
                  this.messages.push({ type: 'ai', content: res.response });
                  this.router.navigate(['/chat', this.threadId]);
              } else {
                  this.messages.push({ type: 'ai', content: res.response });
              }
              this.sending = false;
          },
          error: (err) => {
              console.error(err);
              this.messages.push({ type: 'error', content: 'Failed to send message' });
              this.sending = false;
          }
      });
  }
}
