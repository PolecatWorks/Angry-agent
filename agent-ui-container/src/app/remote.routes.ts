import { Routes } from '@angular/router';
import { MainLayout } from './components/main-layout/main-layout';
import { ChatWindow } from './components/chat-window/chat-window';

export const remoteRoutes: Routes = [
  {
    path: '',
    component: MainLayout,
    children: [
      { path: 'chat', component: ChatWindow },
      { path: 'chat/:threadId', component: ChatWindow },
      { path: 'settings', loadComponent: () => import('./components/settings/settings').then(m => m.SettingsComponent) },
      { path: 'agents', loadComponent: () => import('./components/agents/agents').then(m => m.AgentsComponent) },
      { path: '', redirectTo: 'chat', pathMatch: 'full' }
    ]
  }
];
