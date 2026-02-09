import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatListModule } from '@angular/material/list';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule, Router, NavigationEnd } from '@angular/router';
import { ChatService, Thread } from '../../services/chat.service';
import { filter } from 'rxjs/operators';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-thread-list',
  standalone: true,
  imports: [CommonModule, MatListModule, MatButtonModule, MatIconModule, RouterModule],
  templateUrl: './thread-list.html',
  styleUrls: ['./thread-list.scss']
})
export class ThreadList implements OnInit, OnDestroy {
  threads: Thread[] = [];
  private routerSubscription?: Subscription;
  private threadSubscription?: Subscription;

  constructor(private chatService: ChatService, private router: Router) { }

  ngOnInit() {
    this.loadThreads();

    // Reload threads when navigation ends (e.g., when a new chat is created)
    this.routerSubscription = this.router.events
      .pipe(filter(event => event instanceof NavigationEnd))
      .subscribe(() => {
        this.loadThreads();
      });

    this.threadSubscription = this.chatService.threadCreated$.subscribe(() => {
      this.loadThreads();
    });
  }

  ngOnDestroy() {
    this.routerSubscription?.unsubscribe();
    this.threadSubscription?.unsubscribe();
  }

  loadThreads() {
    this.chatService.getThreads().subscribe({
      next: (res) => {
        this.threads = res.threads;
      },
      error: (err) => console.error(err)
    });
  }

  newChat() {
    this.router.navigate(['/chat']);
  }
}
