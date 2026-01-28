/*
 * Copyright 2012-2019 the original author or authors.
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

import java.util.List;
import java.util.UUID;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.bind.annotation.PostMapping;
import jakarta.validation.Valid;
import org.springframework.validation.BindingResult;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.PathVariable;

/**
 * @author [Your Name]
 */
@Controller
@RequestMapping("/specialties")
class SpecialtyController {

	private final SpecialtyRepository specialtyRepository;

	public SpecialtyController(SpecialtyRepository specialtyRepository) {
		this.specialtyRepository = specialtyRepository;
	}

	@GetMapping("/list")
	public String showSpecialtyList(@RequestParam(defaultValue = "1") int page, Model model) {
		Page<Specialty> paginated = findPaginated(page);
		return addPaginationModel(page, paginated, model);
	}

	private String addPaginationModel(int page, Page<Specialty> paginated, Model model) {
		List<Specialty> listSpecialties = paginated.getContent();
		model.addAttribute("currentPage", page);
		model.addAttribute("totalPages", paginated.getTotalPages());
		model.addAttribute("totalItems", paginated.getTotalElements());
		model.addAttribute("listSpecialties", listSpecialties);
		return "specialties/specialtyList";
	}

	private Page<Specialty> findPaginated(int page) {
		int pageSize = 5;
		Pageable pageable = PageRequest.of(page - 1, pageSize);
		return specialtyRepository.findAll(pageable);
	}

	@GetMapping
	public @ResponseBody List<Specialty> showResourcesSpecialtyList() {
		return this.specialtyRepository.findAll().stream().toList();
	}

	@GetMapping("/new")
	public String initCreationForm(Model model) {
		Specialty specialty = new Specialty();
		model.addAttribute("specialty", specialty);
		return "specialties/createOrUpdateSpecialtyForm";
	}

	@PostMapping("/new")
	public String processCreationForm(@Valid Specialty specialty, BindingResult result) {
		if (result.hasErrors()) {
			return "specialties/createOrUpdateSpecialtyForm";
		}
		specialtyRepository.save(specialty);
		return "redirect:/specialties/list";
	}

	@GetMapping("/edit/{specialtyId}")
	public String initUpdateForm(@PathVariable("specialtyId") UUID specialtyId, Model model) {
		Specialty specialty = specialtyRepository.findById(specialtyId);
		model.addAttribute("specialty", specialty);
		return "specialties/createOrUpdateSpecialtyForm";
	}

	@PostMapping("/edit/{specialtyId}")
	public String processUpdateForm(@PathVariable("specialtyId") UUID specialtyId, @Valid Specialty specialty,
			BindingResult result) {
		if (result.hasErrors()) {
			return "specialties/createOrUpdateSpecialtyForm";
		}
		specialty.setId(specialtyId);
		specialtyRepository.save(specialty);
		return "redirect:/specialties/list";
	}

	@GetMapping("/delete/{specialtyId}")
	public String deleteSpecialty(@PathVariable("specialtyId") UUID specialtyId) {
		Specialty specialty = specialtyRepository.findById(specialtyId);
		specialtyRepository.delete(specialty);
		return "redirect:/specialties/list";
	}

}
