import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatListModule } from '@angular/material/list';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule, Router } from '@angular/router';
import { ChatService, Thread } from '../../services/chat.service';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-thread-list',
  standalone: true,
  imports: [CommonModule, MatListModule, MatButtonModule, MatIconModule, RouterModule],
  template: `
<div class="thread-list-header">
    <h3>History</h3>
    <button mat-stroked-button color="primary" (click)="newChat()" class="new-chat-btn">
        <mat-icon>add</mat-icon>
        New Chat
    </button>
</div>
<mat-nav-list class="thread-nav-list">
    <a mat-list-item *ngFor="let thread of threads$ | async" [routerLink]="['/chat', thread.thread_id]"
        routerLinkActive="active-thread">
        <mat-icon matListItemIcon>chat_bubble_outline</mat-icon>
        <div matListItemTitle>{{ thread.title || 'New Chat' }}</div>
        <div matListItemLine>{{ thread.created_at | date:'short' }}</div>
        <button mat-icon-button matListItemMeta (click)="deleteThread($event, thread.thread_id)">
            <mat-icon>delete</mat-icon>
        </button>
    </a>
</mat-nav-list>
  `,
  styles: [`
.thread-list-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    border-bottom: 1px solid #eee;

    .new-chat-btn {
        display: flex;
        align-items: center;
        gap: 8px;
    }
}

.thread-nav-list {
    padding-top: 8px;

    a[mat-list-item] {
        height: auto;
        min-height: 64px;
        position: relative;

        button[matListItemMeta] {
            position: absolute;
            right: 16px;
            top: 50%;
            transform: translateY(-50%);
        }

        /* Target only the leading icon */
        > .mat-icon {
            color: #757575;
            margin-right: 16px;
        }
    }
}

.active-thread {
    background-color: rgba(63, 81, 181, 0.08) !important;

    .mat-icon {
        color: #3f51b5 !important;
    }
}
  `]
})
export class ThreadList implements OnInit {
  private chatService = inject(ChatService);
  private router = inject(Router);
  threads$ = this.chatService.threads$;

  constructor() { }

  ngOnInit() {
    this.chatService.refreshThreads();
  }

  newChat() {
    this.router.navigate(['/chat']);
  }

  deleteThread(event: Event, threadId: string) {
    event.stopPropagation();
    event.preventDefault();

    if (confirm('Delete this chat?')) {
      this.chatService.deleteThread(threadId).subscribe({
        next: () => {
          this.chatService.refreshThreads();
          // If we are currently on this thread, navigate away
          if (this.router.url.includes('/chat/' + threadId)) {
            this.router.navigate(['/chat']);
          }
        },
        error: (err) => console.error('Error deleting thread', err)
      });
    }
  }
}
