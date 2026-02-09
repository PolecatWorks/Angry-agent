import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { ChatService, Thread } from '../../services/chat.service';
import { ThreadList } from './thread-list';
import { of, Subject, BehaviorSubject } from 'rxjs';
import { vi } from 'vitest';

describe('ThreadList', () => {
  let component: ThreadList;
  let fixture: ComponentFixture<ThreadList>;
  let chatServiceSpy: any;
  let routerSpy: any;

  beforeEach(async () => {
    chatServiceSpy = {
      threads$: new BehaviorSubject([]),
      refreshThreads: vi.fn(),
      getThreads: vi.fn()
    };

    routerSpy = {
      navigate: vi.fn()
    };

    await TestBed.configureTestingModule({
      imports: [ThreadList],
      providers: [
        { provide: ChatService, useValue: chatServiceSpy },
        { provide: Router, useValue: routerSpy },
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: of({ get: (key: string) => null })
          }
        },
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(ThreadList);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should refresh threads on init', () => {
    expect(chatServiceSpy.refreshThreads).toHaveBeenCalled();
  });

  it('should navigate to new chat', () => {
    component.newChat();
    expect(routerSpy.navigate).toHaveBeenCalledWith(['/chat']);
  });
});
