import { Component } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  selector: 'app-error-page',
  standalone: true,
  templateUrl: './error-page.html',
  styleUrls: ['./error-page.scss']
})
export class ErrorPage {
  errorMessage: string = 'An unknown error occurred.';

  constructor(private router: Router) {
    const navigation = this.router.getCurrentNavigation();
    const state = navigation?.extras.state as { error: string };
    if (state && state.error) {
      this.errorMessage = state.error;
    }
  }

  goBack() {
    this.router.navigate(['/']);
  }
}
