package org.springframework.samples.petclinic.config;

import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.CannotAcquireLockException;
import org.springframework.orm.ObjectOptimisticLockingFailureException;
import org.springframework.stereotype.Component;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.TransactionStatus;
import org.springframework.transaction.support.DefaultTransactionDefinition;

@Aspect
@Component
public class TransactionRetryAspect {

	private static final Logger logger = LoggerFactory.getLogger(TransactionRetryAspect.class);

	@Autowired
	private PlatformTransactionManager transactionManager;

	@Around("@annotation(org.springframework.transaction.annotation.Transactional)")
	public Object retryOnLockConflict(ProceedingJoinPoint joinPoint) throws Throwable {

		int maxRetries = 3;
		boolean exponentialBackoff = false;
		int retryCount = 0;
		long waitTime = 1000; // Initial wait time of 1 second

		while (retryCount <= maxRetries) {
			TransactionStatus status = null;
			try {
				logger.info("Accessing via TransactionRetryAspect");

				// Start a new transaction
				DefaultTransactionDefinition def = new DefaultTransactionDefinition();
				def.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
				status = transactionManager.getTransaction(def);

				// Proceed with the method execution
				Object result = joinPoint.proceed();

				// Commit the transaction
				transactionManager.commit(status);

				return result;
			}
			catch (ObjectOptimisticLockingFailureException | CannotAcquireLockException e) {

				// Rollback the transaction
				if (status != null) {
					transactionManager.rollback(status);
				}

				retryCount++;
				if (retryCount > maxRetries) {
					logger.error("Failed to execute after {} attempts", maxRetries, e);
					throw e;
				}

				logger.info("Retrying transaction due to {}. Attempt: {}", e.getClass().getSimpleName(), retryCount);

				if (exponentialBackoff) {
					waitTime *= 2;
				}

				try {
					Thread.sleep(waitTime);
				}
				catch (InterruptedException ie) {
					Thread.currentThread().interrupt();
					throw new RuntimeException("Retry interrupted", ie);
				}
			}
		}

		throw new RuntimeException("Unexpected error in retry logic");
	}

}
