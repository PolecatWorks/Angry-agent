import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

export const devAuthInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);

  // Never manufacture credentials in the browser. A real OIDC
  // access token must be supplied by the authentication integration.
  return next(req).pipe(
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
