import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { SharedContextService } from '@polecatworks/mfe-shared';

export const devAuthInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  let sharedContext: SharedContextService | null = null;
  try {
    sharedContext = inject(SharedContextService);
  } catch {
    // If running in isolation outside MFE shell without provider
    sharedContext = null;
  }

  const token = sharedContext?.getAccessToken();

  let authReq = req;
  if (token) {
    authReq = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
  }

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      // Catch authentication/authorization errors and route to the error page
      if (error.status === 401 || error.status === 403) {
        const errorMsg = error.error?.error || 'Authentication failed. Please check your credentials or access rights.';
        router.navigate(['/error'], { state: { error: errorMsg } });
      }
      return throwError(() => error);
    })
  );
};
