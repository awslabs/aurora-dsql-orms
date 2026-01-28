/*
 * Copyright 2012-2019 the original authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.springframework.samples.petclinic.Specialty;

import org.springframework.cache.annotation.Cacheable;
import org.springframework.dao.DataAccessException;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.repository.Repository;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.cache.annotation.CachePut;
import org.springframework.cache.annotation.CacheEvict;

import java.util.Collection;
import java.util.Optional;
import java.util.UUID;

/**
 * Repository class for <code>Specialty</code> domain objects All method names are
 * compliant with Spring Data naming conventions so this interface can easily be extended
 * for Spring Data. See:
 * https://docs.spring.io/spring-data/jpa/docs/current/reference/html/#repositories.query-methods.query-creation
 *
 * @author [Your Name]
 */
public interface SpecialtyRepository extends Repository<Specialty, Integer> {

	/**
	 * Retrieve all <code>Specialty</code>s from the data store.
	 * @return a <code>Collection</code> of <code>Specialty</code>s
	 */
	@Transactional(readOnly = true)
	@Cacheable(value = "allSpecialties")
	Collection<Specialty> findAll() throws DataAccessException;

	/**
	 * Retrieve all <code>Specialty</code>s from data store in Pages
	 * @param pageable
	 * @return
	 * @throws DataAccessException
	 */
	@Transactional(readOnly = true)
	Page<Specialty> findAll(Pageable pageable);

	/**
	 * Retrieve a <code>Specialty</code> from the data store by id.
	 * @param id the id to search for
	 * @return the <code>Specialty</code> if found
	 */
	@Transactional(readOnly = true)
	@Cacheable(value = "specialty", key = "#id.toString()")
	Specialty findById(UUID id);

	@CachePut(value = "specialty", key = "#result.id.toString()")
	@CacheEvict(value = "allSpecialties", allEntries = true)
	Specialty save(Specialty specialty);

	@CacheEvict(value = { "specialty", "allSpecialties" }, key = "#specialty.id.toString()")
	void delete(Specialty specialty);

}
