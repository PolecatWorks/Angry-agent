import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ChatService, Thread, ChatResponse, HistoryResponse } from './chat.service';
import { AuthService } from './auth.service';
import { vi } from 'vitest';

describe('ChatService', () => {
    let service: ChatService;
    let httpMock: HttpTestingController;
    let authServiceSpy: any;

    beforeEach(() => {
        // Create mock using plain object with functions
        authServiceSpy = {
            getUserId: vi.fn(),
            isLoggedIn: vi.fn()
        };
        authServiceSpy.getUserId.mockReturnValue('test-user');

        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule],
            providers: [
                ChatService,
                { provide: AuthService, useValue: authServiceSpy }
            ]
        });
        service = TestBed.inject(ChatService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => {
        httpMock.verify();
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    it('should send a message and return response', () => {
        const mockResponse: ChatResponse = { thread_id: 'thread-1', response: 'Hello user' };
        const message = 'Hello';

        service.sendMessage(message).subscribe(response => {
            expect(response).toEqual(mockResponse);
        });

        const req = httpMock.expectOne('http://localhost:8000/api/chat');
        expect(req.request.method).toBe('POST');
        expect(req.request.body).toEqual({ message, thread_id: undefined });
        expect(req.request.headers.get('X-User-ID')).toBe('test-user');
        req.flush(mockResponse);
    });

    it('should send a message with threadId', () => {
        const mockResponse: ChatResponse = { thread_id: 'thread-1', response: 'Hello again' };
        const message = 'How are you?';
        const threadId = 'thread-1';

        service.sendMessage(message, threadId).subscribe(response => {
            expect(response).toEqual(mockResponse);
        });

        const req = httpMock.expectOne('http://localhost:8000/api/chat');
        expect(req.request.method).toBe('POST');
        expect(req.request.body).toEqual({ message, thread_id: threadId });
        req.flush(mockResponse);
    });

    it('should get threads', () => {
        const mockThreads: Thread[] = [
            { thread_id: '1', user_id: 'test-user', title: 'Thread 1' },
            { thread_id: '2', user_id: 'test-user', title: 'Thread 2' }
        ];

        service.getThreads().subscribe(response => {
            expect(response.threads).toEqual(mockThreads);
        });

        const req = httpMock.expectOne('http://localhost:8000/api/threads');
        expect(req.request.method).toBe('GET');
        expect(req.request.headers.get('X-User-ID')).toBe('test-user');
        req.flush({ threads: mockThreads });
    });

    it('should get history', () => {
        const mockHistory: HistoryResponse = {
            messages: [
                { type: 'human', content: 'Hi' },
                { type: 'ai', content: 'Hello' }
            ]
        };
        const threadId = 'thread-1';

        service.getHistory(threadId).subscribe(response => {
            expect(response).toEqual(mockHistory);
        });

        const req = httpMock.expectOne(`http://localhost:8000/api/threads/${threadId}/history`);
        expect(req.request.method).toBe('GET');
        req.flush(mockHistory);
    });
});
