import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatListModule } from '@angular/material/list';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { RouterModule, Router, ActivatedRoute } from '@angular/router';
import { ChatService, Thread } from '../../services/chat.service';
import { Observable } from 'rxjs';
import { SharedContextService } from 'mfe-shared';

@Component({
  selector: 'app-thread-list',
  standalone: true,
  imports: [CommonModule, MatListModule, MatButtonModule, MatIconModule, MatMenuModule, RouterModule],
  templateUrl: './thread-list.html',
  styleUrls: ['./thread-list.scss']
})
export class ThreadList implements OnInit {
  private chatService = inject(ChatService);
  // sharedContext: SharedContextService = inject(SharedContextService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  threads$ = this.chatService.threads$;

  colors = [
    { name: 'Default Blue', value: '#3f51b5' },
    { name: 'Green', value: '#4caf50' },
    { name: 'Purple', value: '#9c27b0' },
    { name: 'Orange', value: '#ff9800' },
    { name: 'Teal', value: '#009688' },
    { name: 'Red', value: '#f44336' },
  ];

  constructor(
    public sharedContext: SharedContextService
  ) {
    this.sharedContext.context$.subscribe((user: any) => {
      console.log('User:', user);
    });

  }

  ngOnInit() {
    this.sharedContext.context$.subscribe((user: any) => {
      console.log('Shared Context User:', user);
    });
    this.chatService.refreshThreads();
  }

  newChat() {
    this.router.navigate(['chat'], { relativeTo: this.route });
  }

  deleteThread(event: Event, threadId: string) {
    event.stopPropagation();
    event.preventDefault();

    if (confirm('Delete this chat?')) {
      this.chatService.deleteThread(threadId).subscribe({
        next: () => {
          this.chatService.refreshThreads();
          // If we are currently on this thread, navigate away
          // We check for the threadId in the URL, simpler than traversing route tree
          if (this.router.url.includes(threadId)) {
            this.router.navigate(['chat'], { relativeTo: this.route });
          }
        },
        error: (err) => console.error('Error deleting thread', err)
      });
    }
  }

  changeColor(event: Event, threadId: string, color: string) {
    event.stopPropagation();
    event.preventDefault();
    this.chatService.updateThreadColor(threadId, color).subscribe({
      next: () => {
        this.chatService.refreshThreads();
      },
      error: (err) => console.error('Error updating color', err)
    });
  }
}
