import { Routes } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { MainLayout } from './components/main-layout/main-layout';
import { ChatWindow } from './components/chat-window/chat-window';

export const remoteRoutes: Routes = [
  {
    path: '',
    component: MainLayout,
    providers: [
      provideHttpClient()
    ],
    children: [
      { path: 'chat', component: ChatWindow },
      { path: 'chat/:threadId', component: ChatWindow },
      { path: '', redirectTo: 'chat', pathMatch: 'full' }
    ]
  }
];
