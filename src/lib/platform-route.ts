import { NextResponse } from "next/server";
import {
  PlatformAuthError,
  PlatformPermissionError,
  QuotaError,
} from "./platform-context";
import { PaymentRequiredError } from "./platform-credits";

export function platformErrorResponse(error: unknown): NextResponse | null {
  if (error instanceof PlatformAuthError) {
    return NextResponse.json(
      { error: error.message },
      { status: error.status }
    );
  }
  if (error instanceof QuotaError) {
    return NextResponse.json(
      { error: error.message, quota: error.quota },
      { status: error.status }
    );
  }
  if (error instanceof PlatformPermissionError) {
    return NextResponse.json(
      { error: error.message },
      { status: error.status }
    );
  }
  if (error instanceof PaymentRequiredError) {
    return NextResponse.json(
      { error: error.message },
      { status: error.status }
    );
  }
  return null;
}
