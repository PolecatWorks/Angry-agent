import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { RouterOutlet, Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { ThreadList } from '../thread-list/thread-list';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [CommonModule, MatSidenavModule, MatToolbarModule, MatIconModule, MatButtonModule, RouterOutlet, ThreadList],
  templateUrl: './main-layout.html',
  styleUrls: ['./main-layout.scss']
})
export class MainLayout {
  constructor(private authService: AuthService, private router: Router) {}

  logout() {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
