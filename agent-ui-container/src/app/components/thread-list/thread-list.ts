import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatListModule } from '@angular/material/list';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule, Router, ActivatedRoute } from '@angular/router';
import { ChatService, Thread } from '../../services/chat.service';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-thread-list',
  standalone: true,
  imports: [CommonModule, MatListModule, MatButtonModule, MatIconModule, RouterModule],
  templateUrl: './thread-list.html',
  styleUrls: ['./thread-list.scss']
})
export class ThreadList implements OnInit {
  private chatService = inject(ChatService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  threads$ = this.chatService.threads$;

  constructor() { }

  ngOnInit() {
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
}
