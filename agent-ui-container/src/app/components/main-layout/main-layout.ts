import { Component, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatSidenavModule } from '@angular/material/sidenav';
import { RouterOutlet } from '@angular/router';
import { Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { ThreadList } from '../thread-list/thread-list';
import { VisualizationsPanel } from '../visualizations-panel/visualizations-panel';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [CommonModule, MatSidenavModule, RouterOutlet, ThreadList, VisualizationsPanel],
  templateUrl: './main-layout.html',
  styleUrls: ['./main-layout.scss']
})
export class MainLayout {
  activeThreadId: string | null = null;
  workspaceWidth = 450;
  isResizing = false;

  constructor(private router: Router) {
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe((event: any) => {
      // Extract threadId from URL if present (e.g. /chat/123-abc)
      const urlMatches = event.urlAfterRedirects.match(/\/chat\/([^\/]+)/);
      if (urlMatches && urlMatches[1]) {
        this.activeThreadId = urlMatches[1];
      } else {
        this.activeThreadId = null;
      }
    });
  }

  startResizing(event: MouseEvent) {
    this.isResizing = true;
    event.preventDefault();
  }

  @HostListener('window:mousemove', ['$event'])
  onMouseMove(event: MouseEvent) {
    if (!this.isResizing) return;
    
    // Width is calculated from right edge of window
    const newWidth = window.innerWidth - event.clientX;
    
    // Bounds (e.g. 300px to 800px)
    if (newWidth > 320 && newWidth < 850) {
      this.workspaceWidth = newWidth;
    }
  }

  @HostListener('window:mouseup')
  onMouseUp() {
    this.isResizing = false;
  }
}
