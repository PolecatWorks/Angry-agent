import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly USER_KEY = 'agent-user-id';
  private readonly DEFAULT_USER = 'default-user';

  constructor() { }

  login(username: string): void {
    localStorage.setItem(this.USER_KEY, username);
  }

  logout(): void {
    localStorage.removeItem(this.USER_KEY);
  }

  getUserId(): string {
    // Always return a user ID to simulate being logged in
    let stored = localStorage.getItem(this.USER_KEY);
    if (!stored) {
      stored = this.DEFAULT_USER;
      localStorage.setItem(this.USER_KEY, stored);
    }
    return stored;
  }

  isLoggedIn(): boolean {
    return true; // Always logged in
  }
}
