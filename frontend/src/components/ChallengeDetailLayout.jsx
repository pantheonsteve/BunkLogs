/**
 * Shared classroom-challenge detail: faculty inbox and madrich log.
 *
 * The top back link stays; Done is the primary way out after a reply
 * (faculty) or on a challenge that has already been filed (madrich).
 */
import { Link } from 'react-router-dom';
import Badge from './ui/Badge';
import Button from './ui/Button';
import Card, { CardBody } from './ui/Card';
import PageHeader from './ui/PageHeader';

const STATUS_TONE = {
  open: 'warn',
  acknowledged: 'info',
  resolved: 'ok',
};

function statusLabel(status) {
  if (!status) return 'Unknown';
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export default function ChallengeDetailLayout({
  backTo,
  backLabel,
  backTestId,
  title,
  status,
  statusTestId,
  meta,
  metaTestId,
  body,
  bodyTestId,
  responses = [],
  responsesLabel = 'Responses',
  emptyResponses = 'No responses yet.',
  emptyResponsesTestId,
  responseTestId,
  showDone = false,
  doneTo,
  doneTestId,
  children,
}) {
  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-2xl mx-auto space-y-4">
      <PageHeader
        title={title}
        backTo={backTo}
        backLabel={backLabel}
        backTestId={backTestId}
        actions={(
          <Badge tone={STATUS_TONE[status] || 'neutral'} data-testid={statusTestId}>
            {statusLabel(status)}
          </Badge>
        )}
      >
        {meta && (
          <p className="text-[15px] text-ink-2 mt-1.5" data-testid={metaTestId}>
            {meta}
          </p>
        )}
      </PageHeader>

      <Card>
        <CardBody>
          <p className="text-ink whitespace-pre-wrap" data-testid={bodyTestId}>
            {body}
          </p>
        </CardBody>
      </Card>

      {children}

      <section aria-label={responsesLabel} className="space-y-3">
        <h2 className="text-sm font-semibold text-muted uppercase tracking-wide">
          {responsesLabel}
        </h2>
        {responses.length === 0 ? (
          <p className="text-sm text-muted" data-testid={emptyResponsesTestId}>
            {emptyResponses}
          </p>
        ) : (
          <ul className="space-y-3">
            {responses.map((response) => (
              <li key={response.id}>
                <Card data-testid={responseTestId ? responseTestId(response.id) : undefined}>
                  <CardBody>
                    <p className="text-sm font-medium text-ink">{response.author}</p>
                    <p className="text-ink-2 mt-1 whitespace-pre-wrap">{response.body}</p>
                  </CardBody>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>

      {showDone && doneTo && (
        <div className="pt-2">
          <Button as={Link} to={doneTo} data-testid={doneTestId}>
            Done
          </Button>
        </div>
      )}
    </div>
  );
}
