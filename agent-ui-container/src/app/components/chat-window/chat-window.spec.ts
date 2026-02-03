import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { ChatWindow } from './chat-window';
import { ChatService, Message } from '../../services/chat.service';
import { of } from 'rxjs';
import { By } from '@angular/platform-browser';
import { ChangeDetectorRef } from '@angular/core';
import { vi } from 'vitest';

describe('ChatWindow', () => {
  let component: ChatWindow;
  let fixture: ComponentFixture<ChatWindow>;
  let chatServiceSpy: any;
  let routerSpy: any;

  beforeEach(async () => {
    chatServiceSpy = {
      getHistory: vi.fn(),
      sendMessage: vi.fn()
    };
    routerSpy = {
      navigate: vi.fn()
    };

    // Default mock returns
    chatServiceSpy.getHistory.mockReturnValue(of({ messages: [] }));

    await TestBed.configureTestingModule({
      imports: [ChatWindow],
      providers: [
        { provide: ChatService, useValue: chatServiceSpy },
        { provide: Router, useValue: routerSpy },
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: of({ get: (key: string) => null })
          }
        }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(ChatWindow);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load history when threadId is present', () => {
    // Re-configure for this specific test
    const threadId = 'thread-1';
    const mockMessages: Message[] = [{ type: 'ai', content: 'Hello' }];
    chatServiceSpy.getHistory.mockReturnValue(of({ messages: mockMessages }));

    // Manually trigger ngOnInit with new params or call loadHistory directly
    component.loadHistory(threadId);

    expect(chatServiceSpy.getHistory).toHaveBeenCalledWith(threadId);
    expect(component.messages).toEqual(mockMessages);
  });

  it('should send a message', () => {
    const message = 'Hello world';
    const response = { thread_id: 'thread-1', response: 'Hi there' };
    chatServiceSpy.sendMessage.mockReturnValue(of(response));

    component.newMessage = message;
    component.sendMessage();

    expect(chatServiceSpy.sendMessage).toHaveBeenCalledWith(message, undefined);
    expect(component.messages.length).toBe(2); // Human + AI
    expect(component.messages[1].content).toBe('Hi there');
  });

  it('should navigate to new thread on first message', () => {
    const message = 'New Thread';
    const response = { thread_id: 'new-thread', response: 'Created' };
    chatServiceSpy.sendMessage.mockReturnValue(of(response));

    component.threadId = null;
    component.newMessage = message;
    component.sendMessage();

    expect(routerSpy.navigate).toHaveBeenCalledWith(['/chat', 'new-thread']);
  });
});
